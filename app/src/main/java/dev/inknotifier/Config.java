package dev.inknotifier;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import org.json.JSONObject;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.io.File;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

public final class Config {
    public final String server, pair, role;
    public final byte[] key;
    private Config(JSONObject o) throws Exception {
        server = o.getString("server").replaceAll("/+$", "");
        URI u = new URI(server);
        if (!"https".equals(u.getScheme()) || u.getHost() == null || u.getUserInfo() != null ||
            u.getQuery() != null || u.getFragment() != null || (u.getPath() != null && !u.getPath().isEmpty()))
            throw new IllegalArgumentException("服务器必须是 HTTPS 地址，例如 https://ntfy.sh");
        pair = o.getString("pair");
        if (!pair.matches("[a-f0-9]{48}")) throw new IllegalArgumentException("无效的配对通道");
        key = Crypto.decode(o.getString("key"));
        if (key.length != 32) throw new IllegalArgumentException("无效的配对密钥");
        role = o.getString("role");
        if (!role.equals("sender") && !role.equals("receiver")) throw new IllegalArgumentException("请选择设备角色");
    }
    public String dataTopic() { return "ink-d-" + pair; }
    public String ackTopic() { return "ink-a-" + pair; }
    public static SharedPreferences prefs(Context c) { return c.getSharedPreferences("ink", Context.MODE_PRIVATE); }
    public static SharedPreferences state(Context c) { return c.getSharedPreferences("state", Context.MODE_PRIVATE); }
    private static SecretKey storageKey() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore"); ks.load(null);
        if (!ks.containsAlias("ink-pair-v1")) {
            KeyGenerator kg = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            kg.init(new KeyGenParameterSpec.Builder("ink-pair-v1", KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build());
            kg.generateKey();
        }
        return (SecretKey) ks.getKey("ink-pair-v1", null);
    }
    public static Config load(Context c) {
        try {
            String sealed = prefs(c).getString("sealed", "");
            return sealed.isEmpty() ? null : new Config(new JSONObject(Crypto.open(storageKey(), sealed)));
        } catch (Exception e) { state(c).edit().putString("error", "配对信息无法解锁，请重新配对").apply(); return null; }
    }
    public static void save(Context c, JSONObject o) throws Exception {
        Config cfg = new Config(o);
        prefs(c).edit().putString("sealed", Crypto.seal(storageKey(), o.toString())).putString("role", cfg.role).putBoolean("enabled", false).commit();
        state(c).edit().clear().commit();
    }
    public static JSONObject newPair(String server) throws Exception {
        StringBuilder hex = new StringBuilder(); for (byte b : Crypto.random(24)) hex.append(String.format("%02x", b & 255));
        return new JSONObject().put("server", server).put("pair", hex.toString()).put("key", Crypto.encode(Crypto.random(32)));
    }
    public static String exportCode(Config c) throws Exception {
        return "INK1:" + Crypto.encode(new JSONObject().put("server", c.server).put("pair", c.pair).put("key", Crypto.encode(c.key)).toString().getBytes(StandardCharsets.UTF_8));
    }
    public static JSONObject importCode(String code, String role) throws Exception {
        if (!code.trim().startsWith("INK1:")) throw new IllegalArgumentException("配对码应以 INK1: 开头");
        JSONObject o = new JSONObject(new String(Crypto.decode(code.trim().substring(5)), StandardCharsets.UTF_8));
        o.put("role", role); new Config(o); return o;
    }
    public static boolean enabled(Context c) { return prefs(c).getBoolean("enabled", false); }
    public static Set<String> apps(Context c) {
        return new HashSet<>(prefs(c).getStringSet("apps", new HashSet<>(Arrays.asList("com.tencent.mm", "com.android.mms", "com.google.android.apps.messaging"))));
    }
    public static boolean allowed(Context c, String pkg) { return apps(c).contains(pkg) || (BuildConfig.DEBUG && pkg.equals("com.android.shell")); }
    public static void debugProvision(Context c) {
        if (!BuildConfig.DEBUG) return;
        File file = new File(c.getFilesDir(), "pairing.json");
        if (!file.exists()) return;
        try { save(c, new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8))); }
        catch (Exception e) { android.util.Log.e("InkConfig", e.getClass().getName()+" at "+e.getStackTrace()[0]); state(c).edit().putString("error", "调试配对导入失败").apply(); }
        finally { file.delete(); }
    }
}
