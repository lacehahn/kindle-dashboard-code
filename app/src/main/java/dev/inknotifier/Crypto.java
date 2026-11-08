package dev.inknotifier;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class Crypto {
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final byte[] AAD = "InkNotifier/v1".getBytes(StandardCharsets.UTF_8);
    public static byte[] random(int count) { byte[] b = new byte[count]; RANDOM.nextBytes(b); return b; }
    public static String encode(byte[] b) { return Base64.getUrlEncoder().withoutPadding().encodeToString(b); }
    public static byte[] decode(String s) { return Base64.getUrlDecoder().decode(s); }
    public static String encrypt(byte[] key, String plaintext) throws Exception { return seal(new SecretKeySpec(key, "AES"), plaintext); }
    public static String decrypt(byte[] key, String envelope) throws Exception { return open(new SecretKeySpec(key, "AES"), envelope); }
    public static String seal(SecretKey key, String plaintext) throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        // Android Keystore requires provider-generated IVs for its non-exportable storage key.
        c.init(Cipher.ENCRYPT_MODE, key); byte[] nonce = c.getIV(); c.updateAAD(AAD);
        byte[] encrypted = c.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
        byte[] combined = new byte[nonce.length + encrypted.length];
        System.arraycopy(nonce, 0, combined, 0, 12); System.arraycopy(encrypted, 0, combined, 12, encrypted.length);
        return "v1." + encode(combined);
    }
    public static String open(SecretKey key, String envelope) throws Exception {
        if (!envelope.startsWith("v1.") || envelope.length() > 10000) throw new IllegalArgumentException("Invalid envelope");
        byte[] b = decode(envelope.substring(3));
        if (b.length < 28) throw new IllegalArgumentException("Short envelope");
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, Arrays.copyOfRange(b, 0, 12))); c.updateAAD(AAD);
        return new String(c.doFinal(b, 12, b.length - 12), StandardCharsets.UTF_8);
    }
}
