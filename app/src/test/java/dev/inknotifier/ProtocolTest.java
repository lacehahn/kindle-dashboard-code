package dev.inknotifier;

import org.junit.Test;
import static org.junit.Assert.*;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

public class ProtocolTest {
    @Test public void encryptionRoundTripAndUniqueNonce() throws Exception {
        byte[] key=Crypto.random(32);String text="微信 · 张三\n你好 📖";
        String a=Crypto.encrypt(key,text),b=Crypto.encrypt(key,text);
        assertEquals(text,Crypto.decrypt(key,a));assertNotEquals(a,b);assertFalse(a.contains("微信"));
    }
    @Test public void alteredCiphertextAndWrongKeyAreRejected() throws Exception {
        byte[] key=Crypto.random(32);String original=Crypto.encrypt(key,"private notification");
        byte[] packet=Crypto.decode(original.substring(3));packet[15]^=1;
        try{Crypto.decrypt(key,"v1."+Crypto.encode(packet));fail("tamper accepted");}catch(javax.crypto.AEADBadTagException expected){}
        try{Crypto.decrypt(Crypto.random(32),original);fail("wrong key accepted");}catch(javax.crypto.AEADBadTagException expected){}
    }
    @Test public void unicodeTruncationPreservesCodePointsAndFitsNtfy() throws Exception {
        String content="汉字📖".repeat(2000);String clipped=Protocol.clip(content,1500);
        assertTrue(clipped.getBytes(StandardCharsets.UTF_8).length<=1500);
        assertFalse(clipped.contains("\uFFFD"));
        JSONObject event=Protocol.message("微信","com.tencent.mm","张三",content,UUID.randomUUID().toString(),1,System.currentTimeMillis());
        Protocol.validate(event,"message");assertTrue(Crypto.encrypt(Crypto.random(32),event.toString()).getBytes(StandardCharsets.UTF_8).length<4096);
    }
    @Test public void escapingDoesNotOverflowServicePayload() throws Exception {
        JSONObject event=Protocol.message("\\\"".repeat(200),"a".repeat(300),"\\\"".repeat(300),"\\\"".repeat(2000),UUID.randomUUID().toString(),1,System.currentTimeMillis());
        assertTrue(Crypto.encrypt(Crypto.random(32),event.toString()).length()<4096);
    }
    @Test public void wrongDirectionAndExpiredMessagesAreRejected() throws Exception {
        JSONObject event=Protocol.message("SMS","sms","title","body",UUID.randomUUID().toString(),1,System.currentTimeMillis());
        try{Protocol.validate(event,"ack");fail("wrong direction accepted");}catch(IllegalArgumentException expected){}
        event.put("expires",System.currentTimeMillis()-1);
        try{Protocol.validate(event,"message");fail("expired message accepted");}catch(IllegalArgumentException expected){}
    }
}
