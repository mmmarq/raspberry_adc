#Define o canal default de dados
sudo i2cget -y 1 0x48 0x03

#Le valores do conversor
while [ 1 ] ;do sudo i2cget -y 1 0x48 ; sleep 1 ; done

