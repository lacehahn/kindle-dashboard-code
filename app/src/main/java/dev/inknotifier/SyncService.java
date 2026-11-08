package dev.inknotifier;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.net.ConnectivityManager;
import android.net.Network;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import org.json.JSONObject;
import java.io.IOException;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import okhttp3.Call;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.MediaType;
import okhttp3.Response;
import okio.BufferedSource;

public final class SyncService extends Service {
    public static volatile boolean alive=false;
    private static volatile SyncService active;
    private android.os.PowerManager.WakeLock burstLock;
    private final Object reconnectSignal=new Object();
    private volatile int networkEpoch=0;
    public static final String CHANGE="dev.inknotifier.CHANGED";
    private final ExecutorService subscriber=Executors.newSingleThreadExecutor();
    private final ScheduledExecutorService publisher=Executors.newSingleThreadScheduledExecutor();
    private final OkHttpClient http=new OkHttpClient.Builder().connectTimeout(15,TimeUnit.SECONDS).readTimeout(75,TimeUnit.SECONDS).writeTimeout(20,TimeUnit.SECONDS).build();
    private volatile boolean stopped=false, started=false;
    private boolean ackPollScheduled=false;
    private final OkHttpClient shortHttp=new OkHttpClient.Builder().protocols(java.util.Collections.singletonList(okhttp3.Protocol.HTTP_1_1))
        .connectTimeout(12,TimeUnit.SECONDS).readTimeout(12,TimeUnit.SECONDS).writeTimeout(12,TimeUnit.SECONDS).build();
    private volatile Call stream, sending;
    private Config cfg;
    private ConnectivityManager connectivity;
    private long nextPrune=0;
    private final ConnectivityManager.NetworkCallback networkCallback=new ConnectivityManager.NetworkCallback() {
        @Override public void onAvailable(Network n) {
            if(stopped)return;
            synchronized(reconnectSignal) { networkEpoch++; reconnectSignal.notifyAll(); }
            Store.get(SyncService.this).wakeQueue(); Call c=stream; if(c!=null)c.cancel();
        }
    };
    public static void wakeAndSend(Context c) {
        SyncService s=active; if(s==null || s.stopped || !s.started)return;
        s.burstLock.acquire(30000);
        try { s.publisher.execute(s::publishNext); } catch(java.util.concurrent.RejectedExecutionException ignored) {}
    }
    private void releaseBurstIfIdle() {
        if(Store.get(this).count("outbox",null)==0 && burstLock!=null && burstLock.isHeld()) {
            try { burstLock.release(); } catch(RuntimeException ignored) {}
        }
    }
    public static void changed(Context c) { c.sendBroadcast(new Intent(CHANGE).setPackage(c.getPackageName())); }
    private void status(boolean connected,String error) {
        Config.state(this).edit().putBoolean("connected",connected).putString("error",error).apply();
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.notify(1,foreground(connected?"网络通道已连接":"正在连接 · 断线后自动重试")); changed(this);
    }
    @Override public void onCreate() {
        super.onCreate(); alive=true; active=this;
        burstLock=getSystemService(android.os.PowerManager.class).newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK,"InkNotifier:message-burst");
        burstLock.setReferenceCounted(false); channels();
        Notification n=foreground("正在启动同步");
        if(Build.VERSION.SDK_INT>=34) startForeground(1,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_REMOTE_MESSAGING); else startForeground(1,n);
        Config.state(this).edit().putBoolean("running",true).putBoolean("connected",false).apply();
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if(!Config.enabled(this) || (cfg=Config.load(this))==null) { stopSelf(); return START_NOT_STICKY; }
        if(!started) {
            if(cfg.role.equals("sender") && getSystemService(NotificationManager.class).isNotificationListenerAccessGranted(new android.content.ComponentName(this,NotificationBridge.class)))
                android.service.notification.NotificationListenerService.requestRebind(new android.content.ComponentName(this,NotificationBridge.class));
            started=true;
            connectivity=getSystemService(ConnectivityManager.class);
            connectivity.registerDefaultNetworkCallback(networkCallback);
            subscriber.execute(this::subscribe);
            publisher.scheduleWithFixedDelay(this::publishNext,0,1,TimeUnit.SECONDS);
        }
        if(intent!=null && "test".equals(intent.getAction()) && cfg.role.equals("sender")) {
            try { Store.get(this).enqueueNotification(cfg,"test-"+System.nanoTime(),"墨信测试",getPackageName(),"两台手机已配对","这是一条加密测试通知。离开 Wi-Fi 后，也可以通过移动网络同步。",System.currentTimeMillis()); wakeAndSend(this); changed(this); }
            catch(Exception e) { Config.state(this).edit().putString("error","测试消息入队失败").apply(); }
        }
        return START_STICKY;
    }
    private void subscribe() {
        int failures=0;
        while(!stopped) {
            int epoch=networkEpoch;
            try {
                String topic=cfg.role.equals("sender")?cfg.ackTopic():cfg.dataTopic();
                // Replay service cache; authenticated event IDs make this idempotent.
                Request request=new Request.Builder().url(cfg.server+"/"+topic+"/json?since=all").build();
                stream=http.newCall(request);
                try(Response response=stream.execute()) {
                    if(!response.isSuccessful() || response.body()==null) throw new IOException("HTTP "+response.code());
                    BufferedSource source=response.body().source();
                    String line;
                    while(!stopped && (line=source.readUtf8Line())!=null) {
                        if(line.length()>20000)continue;
                        JSONObject wire=new JSONObject(line);
                        String type=wire.optString("event");
                        if(type.equals("open") || type.equals("keepalive")) { failures=0; status(true,""); }
                        if(type.equals("message")) consume(wire.optString("message"));
                    }
                    if(!stopped) throw new IOException("Stream ended");
                }
            } catch(Exception e) {
                if(stopped)break;
                status(false,"网络连接中断，正在重试");
                long delay=Math.min(60000,1000L << Math.min(failures++,6));
                try { synchronized(reconnectSignal) { if(networkEpoch==epoch && !stopped)reconnectSignal.wait(delay); } } catch(InterruptedException interrupted) { break; }
                if(networkEpoch!=epoch)failures=0;
            }
        }
    }
    private void consume(String encrypted) {
        try {
            JSONObject event=new JSONObject(Crypto.decrypt(cfg.key,encrypted));
            String expected=cfg.role.equals("sender")?"ack":"message"; Protocol.validate(event,expected);
            String id=event.getString("id");
            if(expected.equals("ack")) {
                if(Store.get(this).delivered(id)) {
                    Config.state(this).edit().putLong("lastAck",System.currentTimeMillis()).putInt("delivered",Config.state(this).getInt("delivered",0)+1).putString("sendError","").apply();
                    releaseBurstIfIdle();
                    if(BuildConfig.DEBUG)Log.i("InkSync","ACK "+id); changed(this);
                }
            } else {
                boolean fresh=Store.get(this).receive(event);
                JSONObject ack=Protocol.ack(id);
                Store.get(this).queue(cfg.ackTopic(),id,Crypto.encrypt(cfg.key,ack.toString()),"",ack.getLong("expires")); wakeAndSend(this);
                Config.state(this).edit().putLong("lastReceive",System.currentTimeMillis()).apply();
                if(fresh) { showMessage(event); if(BuildConfig.DEBUG)Log.i("InkSync","RECEIVED "+id); }
                changed(this);
            }
        } catch(Exception rejected) {
            // Forged, expired, or damaged messages must never create a local notification.
            if(BuildConfig.DEBUG)Log.w("InkSync","Rejected unauthenticated or invalid event");
        }
    }
    private void publishNext() {
        if(stopped)return;
        Store.Pending p=null;
        try {
            if(System.currentTimeMillis()>nextPrune) { Store.get(this).prune(); nextPrune=System.currentTimeMillis()+60000; }
            p=Store.get(this).due(); if(p==null)return;
            Request request=new Request.Builder().url(cfg.server+"/"+p.topic).header("Firebase","no")
                .post(RequestBody.create(p.envelope,MediaType.get("text/plain; charset=utf-8"))).build();
            sending=shortHttp.newCall(request);
            try(Response response=sending.execute()) {
                if(!response.isSuccessful()) {
                    long delay=Math.min(300000,5000L << Math.min(p.attempts,6));
                    if(response.code()==429)delay=Math.max(delay,300000);
                    Store.get(this).retry(p.id,delay);
                    Config.state(this).edit().putString("sendError",response.code()==429?"免费服务限流，稍后自动重试":"转发服务返回 "+response.code()+"，正在重试").apply();
                } else {
                    if(cfg.role.equals("receiver")) { Store.get(this).delivered(p.id); releaseBurstIfIdle(); }
                    else { Store.get(this).retry(p.id,p.attempts<2?60000:300000); scheduleAckPoll(0); }
                    Config.state(this).edit().putLong("lastPublish",System.currentTimeMillis()).putString("sendError","").apply();
                    if(BuildConfig.DEBUG)Log.i("InkSync","PUBLISHED "+p.id);
                }
            } changed(this);
        } catch(Exception e) {
            if(p!=null) {
                Store.get(this).retry(p.id,Math.min(300000,5000L << Math.min(p.attempts,6)));
                // The server may have accepted a POST even if its response was lost. Check receipt before retrying.
                if(cfg.role.equals("sender"))scheduleAckPoll(0);
            }
            if(!stopped) { Config.state(this).edit().putString("sendError","发送失败，网络恢复后自动重试").apply(); changed(this); }
        }
    }
    private void scheduleAckPoll(int attempt) {
        if(stopped || ackPollScheduled || Store.get(this).count("outbox",null)==0)return;
        ackPollScheduled=true;
        // A short solicited response also works when a vendor delays the background subscription socket.
        publisher.schedule(()->{
            ackPollScheduled=false;
            if(stopped || Store.get(this).count("outbox",null)==0)return;
            try {
                Request request=new Request.Builder().url(cfg.server+"/"+cfg.ackTopic()+"/json?poll=1&since=5m").build();
                sending=shortHttp.newCall(request);
                try(Response response=sending.execute()) {
                    if(BuildConfig.DEBUG)Log.i("InkSync","ACK_POLL_HTTP "+response.code());
                    if(response.isSuccessful() && response.body()!=null) {
                        String line; BufferedSource source=response.body().source();
                        while((line=source.readUtf8Line())!=null && !stopped) {
                            if(line.length()>20000)continue;
                            JSONObject wire=new JSONObject(line);
                            if("message".equals(wire.optString("event")))consume(wire.optString("message"));
                        }
                    }
                }
            } catch(Exception ignored) { if(BuildConfig.DEBUG)Log.w("InkSync","ACK_POLL_RETRY "+ignored.getClass().getSimpleName()); }
            if(attempt<2)scheduleAckPoll(attempt+1);
        },new long[]{2,5,10}[attempt],TimeUnit.SECONDS);
    }
    private void channels() {
        NotificationManager nm=getSystemService(NotificationManager.class);
        NotificationChannel service=new NotificationChannel("connection","同步连接状态",NotificationManager.IMPORTANCE_LOW); if(Build.VERSION.SDK_INT>=33)service.setBlockable(true); service.setShowBadge(false); service.setSound(null,null); nm.createNotificationChannel(service);
        NotificationChannel normal=new NotificationChannel("messages","同步消息",NotificationManager.IMPORTANCE_DEFAULT); normal.enableVibration(true); nm.createNotificationChannel(normal);
        NotificationChannel quiet=new NotificationChannel("quiet","阅读模式 · 静默消息",NotificationManager.IMPORTANCE_LOW); quiet.setSound(null,null); quiet.enableVibration(false); nm.createNotificationChannel(quiet);
    }
    private PendingIntent openIntent() { return PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE); }
    private Notification foreground(String status) {
        return new Notification.Builder(this,"connection").setSmallIcon(dev.inknotifier.R.drawable.ic_ink).setContentTitle("墨信 · 通知同步")
            .setContentText(status).setContentIntent(openIntent()).setOngoing(true).setOnlyAlertOnce(true).build();
    }
    private void showMessage(JSONObject event) throws Exception {
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return;
        boolean quiet=Config.prefs(this).getBoolean("reading",false);
        String channel=quiet?"quiet":"messages";
        Notification publicVersion=new Notification.Builder(this,channel).setSmallIcon(R.drawable.ic_ink).setContentTitle("墨信").setContentText("收到一条新消息").build();
        String title=event.getString("app")+" · "+event.getString("title");
        Notification n=new Notification.Builder(this,channel).setSmallIcon(R.drawable.ic_ink).setContentTitle(title).setContentText(event.getString("body"))
            .setStyle(new Notification.BigTextStyle().bigText(event.getString("body"))).setVisibility(Notification.VISIBILITY_PRIVATE).setPublicVersion(publicVersion)
            .setContentIntent(openIntent()).setOnlyAlertOnce(true).setAutoCancel(true).setGroup("ink-messages").build();
        getSystemService(NotificationManager.class).notify(event.getString("instance"),2,n);
    }
    @Override public void onDestroy() {
        stopped=true; alive=false; if(active==this)active=null;
        if(burstLock!=null && burstLock.isHeld())try{burstLock.release();}catch(RuntimeException ignored){}
        synchronized(reconnectSignal){reconnectSignal.notifyAll();}
        if(stream!=null)stream.cancel(); if(sending!=null)sending.cancel(); subscriber.shutdownNow(); publisher.shutdownNow();
        if(connectivity!=null)try{connectivity.unregisterNetworkCallback(networkCallback);}catch(RuntimeException ignored){}
        Config.state(this).edit().putBoolean("running",false).putBoolean("connected",false).apply(); changed(this);
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent i) { return null; }
}
