package dev.inknotifier;

import android.content.Context;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public final class Store extends SQLiteOpenHelper {
    private static Store singleton;
    public static synchronized Store get(Context c) { if (singleton == null) singleton = new Store(c.getApplicationContext()); return singleton; }
    private Store(Context c) { super(c, "ink.db", null, 1); }
    @Override public void onCreate(SQLiteDatabase d) {
        d.execSQL("CREATE TABLE outbox(id TEXT PRIMARY KEY,topic TEXT NOT NULL,envelope TEXT NOT NULL,pkg TEXT,expires INTEGER,next INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0)");
        d.execSQL("CREATE TABLE sources(nkey TEXT PRIMARY KEY,instance TEXT NOT NULL,version INTEGER,fingerprint TEXT)");
        d.execSQL("CREATE TABLE inbox(instance TEXT PRIMARY KEY,event TEXT,version INTEGER,posted INTEGER,received INTEGER,app TEXT,pkg TEXT,title TEXT,body TEXT,unread INTEGER DEFAULT 1)");
        d.execSQL("CREATE TABLE seen(id TEXT PRIMARY KEY,expires INTEGER)");
    }
    @Override public void onUpgrade(SQLiteDatabase d, int a, int b) { throw new IllegalStateException("Missing database migration"); }
    public synchronized void reset() { SQLiteDatabase d=getWritableDatabase(); for(String t:new String[]{"outbox","sources","inbox","seen"}) d.delete(t,null,null); }
    public synchronized void prune() {
        SQLiteDatabase d=getWritableDatabase(); long now=System.currentTimeMillis();
        d.delete("outbox","expires < ?",new String[]{""+now}); d.delete("seen","expires < ?",new String[]{""+now});
        d.delete("inbox","received < ?",new String[]{""+(now-Protocol.TTL)});
    }
    public synchronized boolean enqueueNotification(Config cfg, String nkey, String app, String pkg, String title, String body, long posted) throws Exception {
        SQLiteDatabase d=getWritableDatabase(); d.beginTransaction();
        try {
            String instance=UUID.randomUUID().toString(), fingerprint=title+"\n"+body; long version=1;
            try(Cursor c=d.query("sources",null,"nkey=?",new String[]{nkey},null,null,null)) {
                if(c.moveToFirst()) {
                    if(fingerprint.equals(c.getString(c.getColumnIndexOrThrow("fingerprint")))) { d.setTransactionSuccessful(); return false; }
                    instance=c.getString(c.getColumnIndexOrThrow("instance")); version=c.getLong(c.getColumnIndexOrThrow("version"))+1;
                }
            }
            if(count("outbox",null)>=1000) throw new IllegalStateException("待发队列已满，请检查网络");
            JSONObject event=Protocol.message(app,pkg,title,body,instance,version,posted);
            queue(cfg.dataTopic(),event.getString("id"),Crypto.encrypt(cfg.key,event.toString()),pkg,event.getLong("expires"));
            ContentValues values=new ContentValues(); values.put("nkey",nkey); values.put("instance",instance); values.put("version",version); values.put("fingerprint",fingerprint);
            d.insertWithOnConflict("sources",null,values,SQLiteDatabase.CONFLICT_REPLACE);
            d.setTransactionSuccessful(); return true;
        } finally { d.endTransaction(); }
    }
    public synchronized void removeSource(String key) { getWritableDatabase().delete("sources","nkey=?",new String[]{key}); }
    public synchronized void queue(String topic,String id,String envelope,String pkg,long expires) {
        ContentValues v=new ContentValues(); v.put("id",id); v.put("topic",topic); v.put("envelope",envelope); v.put("pkg",pkg); v.put("expires",expires);
        getWritableDatabase().insertWithOnConflict("outbox",null,v,SQLiteDatabase.CONFLICT_IGNORE);
    }
    public static final class Pending { public String id,topic,envelope; public int attempts; }
    public synchronized Pending due() {
        try(Cursor c=getReadableDatabase().query("outbox",null,"next<=? AND expires>=?",new String[]{""+System.currentTimeMillis(),""+System.currentTimeMillis()},null,null,"next ASC","1")) {
            if(!c.moveToFirst()) return null;
            Pending p=new Pending(); p.id=c.getString(c.getColumnIndexOrThrow("id")); p.topic=c.getString(c.getColumnIndexOrThrow("topic")); p.envelope=c.getString(c.getColumnIndexOrThrow("envelope")); p.attempts=c.getInt(c.getColumnIndexOrThrow("attempts")); return p;
        }
    }
    public synchronized void retry(String id,long delay) {
        getWritableDatabase().execSQL("UPDATE outbox SET attempts=attempts+1,next=? WHERE id=?",new Object[]{System.currentTimeMillis()+delay,id});
    }
    public synchronized void wakeQueue() { getWritableDatabase().execSQL("UPDATE outbox SET next=0"); }
    public synchronized boolean delivered(String id) { return getWritableDatabase().delete("outbox","id=?",new String[]{id})>0; }
    public synchronized void purgeDisallowed(java.util.Set<String> allowed) {
        try(Cursor c=getReadableDatabase().rawQuery("SELECT id,pkg FROM outbox WHERE pkg!=''",null)) {
            while(c.moveToNext()) if(!allowed.contains(c.getString(1)) && !(BuildConfig.DEBUG && "com.android.shell".equals(c.getString(1)))) delivered(c.getString(0));
        }
    }
    public synchronized boolean receive(JSONObject event) throws Exception {
        SQLiteDatabase d=getWritableDatabase(); d.beginTransaction();
        try {
            ContentValues seen=new ContentValues(); seen.put("id",event.getString("id")); seen.put("expires",event.getLong("expires"));
            if(d.insertWithOnConflict("seen",null,seen,SQLiteDatabase.CONFLICT_IGNORE)==-1) { d.setTransactionSuccessful(); return false; }
            String instance=event.getString("instance"); long version=event.getLong("version");
            try(Cursor c=d.rawQuery("SELECT version FROM inbox WHERE instance=?",new String[]{instance})) {
                if(c.moveToFirst() && c.getLong(0)>=version) { d.setTransactionSuccessful(); return false; }
            }
            ContentValues v=new ContentValues(); v.put("instance",instance); v.put("event",event.getString("id")); v.put("version",version); v.put("posted",event.getLong("time")); v.put("received",System.currentTimeMillis()); v.put("unread",1);
            for(String key:new String[]{"app","pkg","title","body"}) v.put(key,event.getString(key));
            d.insertWithOnConflict("inbox",null,v,SQLiteDatabase.CONFLICT_REPLACE);
            d.setTransactionSuccessful(); return true;
        } finally { d.endTransaction(); }
    }
    public synchronized int count(String table,String where) {
        // Callers supply only constant table names/clauses, never notification content.
        try(Cursor c=getReadableDatabase().rawQuery("SELECT COUNT(*) FROM "+table+(where==null?"":" WHERE "+where),null)) { c.moveToFirst(); return c.getInt(0); }
    }
    public synchronized List<JSONObject> messages(boolean unread,String search) {
        List<JSONObject> out=new ArrayList<>();
        String where=unread?"unread=1":"1=1"; String[] args=null;
        if(!search.trim().isEmpty()) { where+=" AND (title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' OR app LIKE ? ESCAPE '\\')"; String q="%"+search.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")+"%"; args=new String[]{q,q,q}; }
        try(Cursor c=getReadableDatabase().query("inbox",null,where,args,null,null,"posted DESC","100")) {
            while(c.moveToNext()) {
                JSONObject o=new JSONObject();
                try { for(String key:new String[]{"instance","app","pkg","title","body"}) o.put(key,c.getString(c.getColumnIndexOrThrow(key)));
                    o.put("posted",c.getLong(c.getColumnIndexOrThrow("posted"))).put("unread",c.getInt(c.getColumnIndexOrThrow("unread"))); out.add(o);
                } catch(Exception ignored) { }
            }
        } return out;
    }
    public synchronized void read(String id) { getWritableDatabase().execSQL("UPDATE inbox SET unread=0 WHERE instance=?",new Object[]{id}); }
    public synchronized void readAll() { getWritableDatabase().execSQL("UPDATE inbox SET unread=0"); }
    public synchronized void deleteMessage(String id) { getWritableDatabase().delete("inbox","instance=?",new String[]{id}); }
    public synchronized void clearInbox() { getWritableDatabase().delete("inbox",null,null); }
}
