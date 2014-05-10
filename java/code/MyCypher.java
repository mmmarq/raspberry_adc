import org.keyczar.*;

/*
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.math.BigInteger;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.InvalidKeySpecException;
import java.security.spec.RSAPrivateKeySpec;
import java.security.spec.RSAPublicKeySpec;
import javax.crypto.Cipher;
*/

public class MyCypher {

	private static final String PVT_KEY_PATH = "/Users/wmm125/code/raspberry_adc/Private";
	private static final String PUB_KEY_PATH = "/Users/wmm125/code/raspberry_adc/Public";
	
	public static void main(String[] args){
	   try{
	   	 System.out.println("-------Crypting Text-------------");
	   	 Encrypter encrypter = new Encrypter(PUB_KEY_PATH);
	   	 String ciphertext = encrypter.encrypt("MaRcElO");
	   	 System.out.println(ciphertext);
	   	 
	   	 System.out.println("-------DeCrypting Text-------------");
	   	 Crypter crypter = new Crypter(PVT_KEY_PATH);
	   	 String plaintext = crypter.decrypt(ciphertext);
	   	 System.out.println(plaintext);
	   	 
	   }catch (org.keyczar.exceptions.KeyczarException e){
	   	 System.err.println("Caught KeyczarException: " + e.getMessage());
	   }
	}   
}

