package dev.inknotifier;

import android.app.Notification;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import org.json.JSONObject;

public final class NotificationBridge extends NotificationListenerService {
    @Override public void onListenerConnected() {
        Config.state(this).edit().putBoolean("listener",true).apply(); SyncService.changed(this);
        // Initial grant does not upload old notifications. Only new events are forwarded.
    }
    @Override public void onListenerDisconnected() { Config.state(this).edit().putBoolean("listener",false).apply(); SyncService.changed(this); }
    @Override public void onNotificationPosted(StatusBarNotification sbn) {
        Config cfg=Config.load(this);
        if(cfg==null || !cfg.role.equals("sender") || !Config.enabled(this)) return;
        String pkg=sbn.getPackageName(); Notification n=sbn.getNotification();
        if(pkg.equals(getPackageName()) || !Config.allowed(this,pkg) || (n.flags & (Notification.FLAG_ONGOING_EVENT | Notification.FLAG_GROUP_SUMMARY))!=0) return;
        Bundle b=n.extras;
        String title=text(b.getCharSequence(Notification.EXTRA_TITLE));
        String body=text(b.getCharSequence(Notification.EXTRA_BIG_TEXT));
        if(body.isEmpty()) body=text(b.getCharSequence(Notification.EXTRA_TEXT));
        android.os.Parcelable[] messages=b.getParcelableArray(Notification.EXTRA_MESSAGES);
        if(messages!=null && messages.length>0 && messages[messages.length-1] instanceof Bundle) {
            Bundle last=(Bundle)messages[messages.length-1]; String message=text(last.getCharSequence("text"));
            if(!message.isEmpty()) body=message;
        }
        if(body.isEmpty()) {
            CharSequence[] lines=b.getCharSequenceArray(Notification.EXTRA_TEXT_LINES);
            if(lines!=null) { StringBuilder all=new StringBuilder(); for(CharSequence l:lines) { if(all.length()>0) all.append('\n'); all.append(l); } body=all.toString(); }
        }
        if(title.isEmpty() && body.isEmpty()) return;
        String app=pkg;
        try { app=getPackageManager().getApplicationLabel(getPackageManager().getApplicationInfo(pkg,0)).toString(); } catch(Exception ignored) { }
        try {
            if(Store.get(this).enqueueNotification(cfg,sbn.getKey(),app,pkg,title,body,sbn.getPostTime())) { SyncService.wakeAndSend(this); SyncService.changed(this); }
        } catch(Exception e) { Config.state(this).edit().putString("error","通知入队失败，请检查存储或连接").apply(); SyncService.changed(this); }
    }
    @Override public void onNotificationRemoved(StatusBarNotification sbn) { Store.get(this).removeSource(sbn.getKey()); }
    private static String text(CharSequence s) { return s==null?"":s.toString(); }
}
