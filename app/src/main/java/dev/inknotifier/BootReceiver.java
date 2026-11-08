package dev.inknotifier;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c,Intent i) {
        if((Intent.ACTION_BOOT_COMPLETED.equals(i.getAction()) || Intent.ACTION_MY_PACKAGE_REPLACED.equals(i.getAction())) && Config.enabled(c) && Config.load(c)!=null) {
            try { c.startForegroundService(new Intent(c,SyncService.class)); }
            catch(RuntimeException e) { Config.state(c).edit().putString("error","系统限制后台启动，请打开墨信恢复连接").apply(); }
        }
    }
}
