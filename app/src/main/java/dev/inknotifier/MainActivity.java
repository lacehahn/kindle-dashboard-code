package dev.inknotifier;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.NotificationManager;
import android.content.BroadcastReceiver;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class MainActivity extends Activity {
    private LinearLayout root,body;
    private TextView status,metrics,notice;
    private Config cfg;
    private String tab="main", search="";
    private boolean unread=false;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final BroadcastReceiver changes=new BroadcastReceiver() {
        @Override public void onReceive(Context c,Intent i) { updateStatus(); }
    };
    private final Runnable tick=new Runnable() { public void run(){updateStatus();handler.postDelayed(this,5000);} };
    @Override public void onCreate(Bundle b) { super.onCreate(b); Config.debugProvision(this); cfg=Config.load(this); render(); }
    @Override public void onResume() {
        super.onResume(); render();
        if(cfg!=null && Config.enabled(this)) {
            try { startForegroundService(new Intent(this,SyncService.class)); }
            catch(RuntimeException e) { Config.state(this).edit().putString("error","请点击重新连接恢复后台服务").apply(); }
        }
        androidx.core.content.ContextCompat.registerReceiver(this,changes,new IntentFilter(SyncService.CHANGE),androidx.core.content.ContextCompat.RECEIVER_NOT_EXPORTED);
        handler.post(tick);
    }
    @Override public void onPause() { handler.removeCallbacks(tick);unregisterReceiver(changes);super.onPause(); }
    private int dp(float n) { return (int)(n*getResources().getDisplayMetrics().density+0.5f); }
    private LinearLayout column() { LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l; }
    private TextView text(String s,float size,boolean bold) {
        TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(Color.rgb(20,20,20));t.setLineSpacing(dp(4),1);
        if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;
    }
    private GradientDrawable background(boolean dark) {
        GradientDrawable d=new GradientDrawable();d.setColor(dark?Color.rgb(20,20,20):Color.WHITE);d.setCornerRadius(dp(5));d.setStroke(dp(1),Color.rgb(20,20,20));return d;
    }
    private Button button(String label,boolean dark,Runnable action) {
        Button b=new Button(this);b.setText(label);b.setTextSize(17);b.setAllCaps(false);b.setTextColor(dark?Color.WHITE:Color.BLACK);b.setBackground(background(dark));b.setMinHeight(dp(52));b.setPadding(dp(12),dp(12),dp(12),dp(12));
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=dp(10);b.setLayoutParams(p);b.setOnClickListener(v->action.run());return b;
    }
    private void gap(int n) { View v=new View(this);body.addView(v,new LinearLayout.LayoutParams(1,dp(n))); }
    private void line() { View v=new View(this);v.setBackgroundColor(Color.rgb(190,190,190));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(1));p.topMargin=dp(16);p.bottomMargin=dp(16);body.addView(v,p); }
    private void heading(String s) { gap(16);body.addView(text(s,24,true));gap(8); }
    private void render() {
        cfg=Config.load(this);root=column();root.setBackgroundColor(Color.WHITE);root.setPadding(dp(20),dp(12),dp(20),dp(10));setContentView(root);
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(dp(20),insets.getSystemWindowInsetTop()+dp(12),dp(20),insets.getSystemWindowInsetBottom()+dp(10));return insets;});root.requestApplyInsets();
        LinearLayout top=new LinearLayout(this);top.setGravity(Gravity.CENTER_VERTICAL);TextView brand=text("墨信",30,true);top.addView(brand,new LinearLayout.LayoutParams(0,-2,1));top.addView(text(cfg==null?"初次使用":cfg.role.equals("sender")?"主设备":"从设备",15,false));root.addView(top);
        TextView subtitle=text("让消息跟上你的阅读",14,false);subtitle.setPadding(0,dp(4),0,dp(12));root.addView(subtitle);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);body=column();body.setPadding(0,0,0,dp(20));scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        status=null;metrics=null;notice=null;
        if(cfg==null){setup();return;}
        status=text("",18,true);metrics=text("",14,false);body.addView(status);gap(5);body.addView(metrics);line();
        if(tab.equals("device"))device();else if(tab.equals("apps"))apps();else if(tab.equals("reading"))reading();else if(cfg.role.equals("sender"))sender();else inbox();
        LinearLayout nav=new LinearLayout(this);String[] names=cfg.role.equals("sender")?new String[]{"同步","应用","设备"}:new String[]{"消息","阅读","设备"};
        String[] ids=cfg.role.equals("sender")?new String[]{"main","apps","device"}:new String[]{"main","reading","device"};
        for(int i=0;i<3;i++){final String id=ids[i];Button b=button(names[i],tab.equals(id),()->{tab=id;render();});LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(50),1);if(i>0)p.leftMargin=dp(8);nav.addView(b,p);}root.addView(nav);updateStatus();
    }
    private void setup() {
        heading("两台手机，一份消息");body.addView(text("主设备发送通知，从设备接收并阅读。两台手机各自联网即可使用。",19,false));gap(24);
        body.addView(button("这是主设备 · 创建配对",true,()->{
            EditText server=input("https://ntfy.sh");server.setText("https://ntfy.sh");
            new AlertDialog.Builder(this).setTitle("选择免费转发服务").setMessage("默认使用 ntfy.sh。仅上传加密内容，公共服务有免费额度。也可输入自己的 HTTPS ntfy 服务器地址。")
                .setView(server).setNegativeButton("取消",null).setPositiveButton("创建",(d,w)->{
                    try{JSONObject o=Config.newPair(server.getText().toString().trim());o.put("role","sender");configure(o);pairCode();}catch(Exception e){toast(e.getMessage());}
                }).show();
        }));
        body.addView(button("这是从设备 · 输入配对码",false,()->{
            EditText code=input("粘贴主设备上的 INK1: 配对码");
            new AlertDialog.Builder(this).setTitle("配对从设备").setView(code).setNegativeButton("取消",null).setPositiveButton("配对",(d,w)->{
                try{configure(Config.importCode(code.getText().toString(),"receiver"));}catch(Exception e){toast("配对码无效，请检查完整内容");}
            }).show();
        }));gap(20);body.addView(text("不需要 root，也不读取聊天数据库。你可以选择哪些应用的通知需要同步。",15,false));
    }
    private EditText input(String hint) { EditText e=new EditText(this);e.setTextColor(Color.BLACK);e.setTextSize(17);e.setHint(hint);e.setPadding(dp(16),dp(12),dp(16),dp(12));return e; }
    private void configure(JSONObject o) throws Exception {
        stopSync();Config.save(this,o);Store.get(this).reset();cfg=Config.load(this);tab="main";render();
    }
    private void sender() {
        heading("把通知送到从设备");body.addView(text("只同步已选择应用的新通知。暂停期间的新通知不会转发。",18,false));
        body.addView(button(Config.enabled(this)?"暂停同步":"开始同步",true,()->{if(Config.enabled(this))stopSync();else startSync(false);render();}));
        body.addView(button("发送测试消息",false,()->{startSync(true);render();}));
        body.addView(button("选择同步应用",false,()->{tab="apps";render();}));
        heading("权限检查");
        TextView listener=text(listenerAllowed()?"✓ 已允许读取通知":"需要允许读取系统通知",18,true);body.addView(listener);
        body.addView(button("打开通知读取授权",false,()->startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))));
        body.addView(button("后台运行设置",false,this::battery));gap(14);
        body.addView(text("微信只能同步通知预览。图片、语音、完整聊天记录及被系统隐藏的验证码无法保证同步。",15,false));
    }
    private void inbox() {
        heading("你的消息");
        EditText filter=input("搜索应用、发送人或内容");filter.setSingleLine(true);filter.setText(search);filter.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        filter.setOnEditorActionListener((v,a,e)->{search=filter.getText().toString();render();return true;});body.addView(filter);
        body.addView(button(unread?"只看未读 · 点击查看全部":"全部消息 · 点击只看未读",false,()->{unread=!unread;search=filter.getText().toString();render();}));
        notice=button("刷新消息",false,()->{search=filter.getText().toString();render();});body.addView(notice);
        List<JSONObject> items=Store.get(this).messages(unread,search);
        if(items.isEmpty()){gap(24);body.addView(text("还没有消息",23,true));gap(8);body.addView(text("在主设备上选择同步应用，然后发送一条测试消息。新消息会出现在这里。",18,false));}
        for(JSONObject m:items) {
            line();LinearLayout card=column();card.setPadding(0,dp(4),0,dp(4));
            card.addView(text((m.optInt("unread")==1?"● ":"")+m.optString("app")+" · "+time(m.optLong("posted")),14,true));
            TextView title=text(m.optString("title"),22,true);title.setPadding(0,dp(8),0,dp(6));card.addView(title);
            TextView excerpt=text(m.optString("body"),20,false);excerpt.setMaxLines(3);card.addView(excerpt);card.setOnClickListener(v->detail(m));body.addView(card);
        }
        if(!items.isEmpty()){gap(14);body.addView(text("显示最近 100 条匹配消息 · 本地保留 7 天",13,false));body.addView(button("全部标记为本地已读",false,()->{Store.get(this).readAll();render();}));}
        if(!Config.enabled(this))body.addView(button("开始接收通知",true,()->{startSync(false);render();}));
    }
    private void detail(JSONObject m) {
        ScrollView scroll=new ScrollView(this);TextView content=text(m.optString("app")+" · "+time(m.optLong("posted"))+"\n\n"+m.optString("title")+"\n\n"+m.optString("body"),20,false);content.setPadding(dp(20),dp(12),dp(20),dp(16));content.setTextIsSelectable(true);scroll.addView(content);
        new AlertDialog.Builder(this).setTitle("消息详情").setView(scroll).setPositiveButton("标记本地已读",(d,w)->{Store.get(this).read(m.optString("instance"));getSystemService(NotificationManager.class).cancel(m.optString("instance"),2);render();})
            .setNeutralButton("删除",(d,w)->{Store.get(this).deleteMessage(m.optString("instance"));getSystemService(NotificationManager.class).cancel(m.optString("instance"),2);render();}).setNegativeButton("关闭",null).show();
    }
    private void reading() {
        heading("少一些打扰");boolean on=Config.prefs(this).getBoolean("reading",false);
        body.addView(text(on?"阅读模式已开启":"阅读模式未开启",22,true));gap(12);body.addView(text("开启后，新消息会静默进入收件箱和通知栏。阅读中的列表不会跳动，点击刷新再查看。",19,false));
        body.addView(button(on?"关闭阅读模式":"开启阅读模式",true,()->{Config.prefs(this).edit().putBoolean("reading",!on).apply();render();}));
        gap(20);body.addView(text("锁屏只显示新消息提示。系统通知的声音和震动，也可以在 Android 通知设置中调整。",16,false));
    }
    private void apps() {
        heading("选择同步应用");body.addView(text("仅选中的应用会转发。取消选择会同时移除该应用尚未发送的消息。",17,false));
        Set<String> selected=Config.apps(this);
        LinkedHashMap<String,String> labels=new LinkedHashMap<>();
        Intent launcher=new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> found=getPackageManager().queryIntentActivities(launcher,0);
        found.sort((a,b)->a.loadLabel(getPackageManager()).toString().compareTo(b.loadLabel(getPackageManager()).toString()));
        for(ResolveInfo r:found) if(!r.activityInfo.packageName.equals(getPackageName()))labels.put(r.activityInfo.packageName,r.loadLabel(getPackageManager()).toString());
        if(BuildConfig.DEBUG)labels.put("com.android.shell","ADB 测试通知（调试版）");
        for(String pkg:selected) if(!labels.containsKey(pkg)) {try{labels.put(pkg,getPackageManager().getApplicationLabel(getPackageManager().getApplicationInfo(pkg,0)).toString());}catch(Exception ignored){}}
        for(java.util.Map.Entry<String,String> item:labels.entrySet()) {
            android.widget.CheckBox box=new android.widget.CheckBox(this);box.setText(item.getValue());box.setTextSize(18);box.setTextColor(Color.BLACK);box.setPadding(0,dp(8),0,dp(8));box.setChecked(selected.contains(item.getKey()) || (BuildConfig.DEBUG && item.getKey().equals("com.android.shell")));box.setMinHeight(dp(52));
            if(BuildConfig.DEBUG && item.getKey().equals("com.android.shell")) {box.setEnabled(false);} else box.setOnCheckedChangeListener((v,on)->{
                Set<String> apps=Config.apps(this);if(on)apps.add(item.getKey());else apps.remove(item.getKey());Config.prefs(this).edit().putStringSet("apps",apps).apply();Store.get(this).purgeDisallowed(apps);updateStatus();
            });body.addView(box);
        }
    }
    private void device() {
        heading("连接与设备");body.addView(text("当前设备："+(cfg.role.equals("sender")?"主设备":"从设备")+"\n系统版本：Android "+Build.VERSION.RELEASE+"（API "+Build.VERSION.SDK_INT+"）\n角色："+(cfg.role.equals("sender")?"发送通知":"接收通知"),17,false));
        gap(16);body.addView(text("网络通道："+cfg.server+"\n加密配对：已启用\n无需连接同一个 Wi-Fi",17,false));
        body.addView(button(Config.enabled(this)?"暂停同步":"开始同步",true,()->{if(Config.enabled(this))stopSync();else startSync(false);render();}));
        body.addView(button("重新连接",false,()->{stopSync();startSync(false);render();}));
        body.addView(button("后台运行设置",false,this::battery));
        body.addView(button("隐藏待机通知",false,()->{Intent i=new Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS);i.putExtra(Settings.EXTRA_APP_PACKAGE,getPackageName());i.putExtra(Settings.EXTRA_CHANNEL_ID,"connection");startActivity(i);}));
        body.addView(text("关闭“同步连接状态”类别即可隐藏待机通知，新消息提醒不受影响。",15,false));
        body.addView(button("系统应用设置",false,()->startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())))));
        if(cfg.role.equals("sender"))body.addView(button("显示配对码",false,this::pairCode));
        body.addView(button("解除配对",false,()->new AlertDialog.Builder(this).setTitle("解除配对？").setMessage("停止同步，删除本机配对密钥、待发队列和消息。另一台设备需要重新配对。")
            .setNegativeButton("取消",null).setPositiveButton("解除",(d,w)->{stopSync();Config.prefs(this).edit().clear().commit();Config.state(this).edit().clear().commit();Store.get(this).reset();getSystemService(NotificationManager.class).cancelAll();tab="main";render();}).show()));
        gap(16);body.addView(text("墨信 0.1.1 · 开发测试版\n免费服务可能限流；锁屏接收速度取决于网络和手机后台策略。",14,false));
    }
    private void pairCode() {
        try{
            String code=Config.exportCode(cfg);TextView t=text(code,14,false);t.setPadding(dp(20),dp(12),dp(20),dp(12));t.setTextIsSelectable(true);
            new AlertDialog.Builder(this).setTitle("在另一台手机输入配对码").setMessage("配对码包含设备密钥，请仅交给你自己的另一台手机。").setView(t).setNegativeButton("关闭",null)
                .setPositiveButton("复制配对码",(d,w)->{getSystemService(ClipboardManager.class).setPrimaryClip(ClipData.newPlainText("墨信配对码",code));toast("已复制配对码");}).show();
        }catch(Exception e){toast("无法导出配对码");}
    }
    private void startSync(boolean test) {
        if(cfg==null)return;
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},10);
        Config.prefs(this).edit().putBoolean("enabled",true).commit();
        try{Intent i=new Intent(this,SyncService.class);if(test)i.setAction("test");startForegroundService(i);if(cfg.role.equals("sender")&&!listenerAllowed())toast("请允许读取通知，测试消息可以先发送");}
        catch(RuntimeException e){Config.prefs(this).edit().putBoolean("enabled",false).apply();toast("无法启动同步，请检查系统后台权限");}
        updateStatus();
    }
    private void stopSync() { Config.prefs(this).edit().putBoolean("enabled",false).commit();stopService(new Intent(this,SyncService.class)); }
    private boolean listenerAllowed() { return getSystemService(NotificationManager.class).isNotificationListenerAccessGranted(new ComponentName(this,NotificationBridge.class)); }
    private void battery() {
        PowerManager p=getSystemService(PowerManager.class);
        if(p.isIgnoringBatteryOptimizations(getPackageName())) {toast("已允许后台运行；部分设备还需在应用设置中允许自启动");startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())));}
        else try{startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,Uri.parse("package:"+getPackageName())));}catch(RuntimeException e){startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));}
    }
    private void updateStatus() {
        if(cfg==null || status==null)return;SharedPreferences s=Config.state(this);
        String label=!Config.enabled(this)?"○ 同步已暂停":!SyncService.alive?"○ 连接服务未运行 · 请重新连接":s.getBoolean("connected",false)?"● 网络通道已连接":"○ 正在重连";
        status.setText(label);
        long last=s.getLong(cfg.role.equals("sender")?"lastAck":"lastReceive",0);
        String detail=(cfg.role.equals("sender")?"设备确认收到：":"最近接收：")+(last==0?"暂无":time(last))+"\n"+(cfg.role.equals("sender")?"待确认消息："+Store.get(this).count("outbox",null):"未读消息："+Store.get(this).count("inbox","unread=1"));
        if(cfg.role.equals("sender")&&!listenerAllowed())detail+="\n请允许读取通知";
        String err=s.getString("sendError","");if(err.isEmpty())err=s.getString("error","");if(!err.isEmpty())detail+="\n"+err;
        metrics.setText(detail);if(notice!=null)notice.setText("刷新消息 · "+Store.get(this).count("inbox","unread=1")+" 条未读");
    }
    private String time(long t) { return new SimpleDateFormat("MM-dd HH:mm",Locale.getDefault()).format(new Date(t)); }
    private void toast(String s) { Toast.makeText(this,s==null?"操作失败":s,Toast.LENGTH_LONG).show(); }
}
