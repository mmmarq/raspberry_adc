import org.keyczar.*;
import org.keyczar.exceptions.KeyczarException;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.InetAddress;
import java.net.Socket;
import java.net.UnknownHostException;


public class MyClient {

	private static final String PVT_KEY_PATH = "/Users/wmm125/code/raspberry_adc/Private";
	private static final String PUB_KEY_PATH = "/Users/wmm125/code/raspberry_adc/Public";
	private static final String SERVER = "192.168.0.122";
	private static final int PORT = 12345;

	public static void main(String[] args){
	   try{
	   	    /*-------Crypting Text-------------*/
	   	    Encrypter encrypter = new Encrypter(PUB_KEY_PATH);
	   	    String ciphertext = encrypter.encrypt("light.status");
	   	    //System.out.println(ciphertext);
	   	    String result = sendServerCommand(ciphertext);
	   	    
	   	    Crypter crypter = new Crypter(PVT_KEY_PATH);
	   	    String plaintext = crypter.decrypt(result);

	   	    if ( plaintext.startsWith("on") ){
	   	    	  System.out.println("Lights on");
	   	    }else{
	   	    	  System.out.println("Lights off");
	   	    }
	   }catch(KeyczarException e){
	   	 System.err.println("Caught KeyczarException: " + e.getMessage());
	   }
	}
	
	private static String sendServerCommand(String command){
	   String commandResult = new String();
    	
	   	 try{
	   	    //Create socket
	   	    InetAddress serverAddr = InetAddress.getByName(SERVER);
	   	    Socket socket = new Socket(serverAddr,PORT);
	   	    
	   	    //Send command to server
	   	    PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(socket.getOutputStream())),true);
	   	    out.println(command);
	   	    //Read server response
	   	    BufferedReader input = new BufferedReader(new InputStreamReader(socket.getInputStream()));
	   	    
	   	    //Convert BufferedReader to string
	   	    String line=null;
	   	    String message = new String();
	   	    while ((line = input.readLine()) != null) {
	   	    	  commandResult += line;
	   	    }
	   	    //Close connection
	   	    socket.close();
	   	 }catch (UnknownHostException e){
	   	    return new String();
	   	 }
	   	 catch (IOException e){
	   	    return new String();
	   	 }
	   return commandResult;
    }
}

