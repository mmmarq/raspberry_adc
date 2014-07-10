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

public class MySigner {

	private static final String SIG_KEY_PATH = "/Users/wmm125/Downloads/signkeys";
	
	public static void main(String[] args){
	   try{
	   	 System.out.println("-------Signing Text-------------");
	   	 Signer signer = new Signer(SIG_KEY_PATH);
	   	 String signature = signer.sign(args[0]);
	   	 System.out.println(args[0]);
	   	 System.out.println(signature);
	   	 
	   	 
	   }catch (org.keyczar.exceptions.KeyczarException e){
	   	 System.err.println("Caught KeyczarException: " + e.getMessage());
	   }
	}   
}

