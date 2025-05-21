# TextToWavFileCLI version 1.0
# Author : Costas Skordis 
# May 2025

"""
Takes the contents of a text file in basic and encodes it into a Kansas
City Standard WAV file, that when played will upload data via the
cassette tape input on the Cosmac ELF II Full Basic Math computers.

The format of the data is the following:

Bit 1 is represented by 2400 Hz
Bit 0 is represented by 800 Hz
There is a leader sequence of 2400Hz Bit 1 for about 14 seconds before the data.
The data block is a start bit of 0, followed by the byte representing the character and then parity bit which by default is odd.
Before the characters of the text file is converted,  a 2 byte data block that contains the total byte size + 256 is processed. 
After this all characters are processed with the data block structure.

At the end there is a data block with 0 Byte value followed by 3 Bit 0 pulses. 

                ______________________________________________________
________________|Repeated as many as there are characters in code    |____
|Leader 14 secs |Start Bit 0|  Character Byte  |Parity Odd Bit       |Terminator|0000|
|@ 2400Hz       |Byte                          |                     |0 Byte    |    |



See http://en.wikipedia.org/wiki/Kansas_City_standard
"""


# A few global parameters related to the encoding

FRAMERATE = 22050      # Hz
ONES_FREQ = 2400       # Hz (per KCS)
ZERO_FREQ = 800        # Hz (per KCS)
AMPLITUDE = 225        # Amplitude of generated square waves
CENTER    = 128        # Center point of generated waves
LEADER    = 14         # Default seconds for leader
PARITY    = 0          # Parity 0 = Odd, 1 = Even
STARTBIT  = 0          # Start Bit

# Create a single square wave cycle of a given frequency
def make_square_wave(freq,framerate):
    n = int(framerate/freq/2)
    return bytearray([CENTER-AMPLITUDE//2])*n + \
           bytearray([CENTER+AMPLITUDE//2])*n

# Create the wave patterns that encode 1s and 0s
one_pulse  = make_square_wave(ONES_FREQ,FRAMERATE) 
zero_pulse = make_square_wave(ZERO_FREQ,FRAMERATE) 

def is_even(number):
    return number % 2 == 0

def Extract_Number_String(text):
    match = re.match(r"^(\d+)(.*)", text)
    if match:
        number_str, remaining_str = match.groups()
        return int(number_str), remaining_str.lstrip()
    else:
        return None, text


def Create_BinData(SourceFile):        
    with open(SourceFile, 'r', encoding='utf-8') as file:
        text_content = file.read()
        text_segment = text_content.split('\n')   # Line and Code
        indexed_data = {i: seg for i, seg in enumerate(text_segment)}
        byte_size= 0
        code_array = []
        start_array=[]
        # Split line into label and code
        for i in range(len(indexed_data)):
            label,code=Extract_Number_String(indexed_data[i])
            if label==None:
                continue
            code=code+"\r"
            #labelcode=str(label)+code
            byte_code = code.encode('utf-8')      # Encode the string to bytes using UTF-8
            label_byte=bin(label)[2:].zfill(16)
            code_array.append(label_byte[0:8]) 
            code_array.append(label_byte[8:])

            for byte in byte_code:
                # Convert each byte to its 8-bit binary representation and append each bit (as an integer) to the binary array
                code_array.append(bin(byte)[2:].zfill(8)) 
    byte_size=len(code_array)
    code_array.append(bin(0)[2:].zfill(8)) # terminating sequence and not included in byte size calculation
   
    start=bin(byte_size+256)[2:].zfill(16) # start at 0x100          
    start_array.append(start[0:8])         # start sequence with byte 1
    start_array.append(start[8:])          # start sequence with byte 2
    binary_array=[]
    binary_array.extend(start_array)
    binary_array.extend(code_array)
    return binary_array
   
# Take a single byte value and turn it into a bytearray representing
# the associated waveform along with the required start and stop bits.
def Encode_Data(bytes):
    # The start bit (0 or 1)
    if (STARTBIT==0):
        encoded = bytearray(zero_pulse)
    else:
        encoded = bytearray(one_pulse)
    p = 0
    # 8 data bits
    for bit in bytes:
        if (int(bit)==1):
            encoded.extend(one_pulse)
            p=p+1
        else:
            encoded.extend(zero_pulse)
            
    # add parity
    
    if (PARITY==0):
        if (p==0) or is_even(p):
            encoded.extend(one_pulse)   
        else:
            encoded.extend(zero_pulse)   
    else:
        if is_even(p)==0:
            encoded.extend(one_pulse)        
        else:
            encoded.extend(zero_pulse)
    return encoded


# Write Tag
def Write_Tag(filename,text1):
    with taglib.File(filename) as file:
        file.tags["ARTIST"] = [text1]    
        file.tags["ALBUM"] = [text1]
        file.tags["TITLE"] = [text1]
        file.save()


# Write a WAV file with encoded data. leader and trailer specify the
# number of seconds of carrier signal to encode before and after the data
def Write_Wav(TargetFile,Binary_Data):
    w = wave.open(TargetFile,"wb")
    w.setnchannels(1)
    w.setsampwidth(1)
    w.setframerate(FRAMERATE)

    # Write the leader
    w.writeframes(one_pulse*(int(FRAMERATE/len(one_pulse))*LEADER))
    # Encode the actual data
    for byte in Binary_Data:
        w.writeframes(Encode_Data(byte))
  
    for x in range(3):
        w.writeframes(zero_pulse) 
    w.close()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 1:
        print("Usage : %s" % sys.argv[0],file=sys.stderr)
        raise SystemExit(1)

    import click,os,re,taglib,wave
    from colorama import Fore, Back, Style, init
    from pathlib import Path
       
    os.system('cls')
    init(autoreset=True)
    print(f'{Fore.RED}{Style.BRIGHT}Basic Text To Wav File Conversion\n')
    print(f'{Fore.GREEN}{Style.BRIGHT}File Settings')
    # Prompts
    SourceDir = click.prompt(f'{Fore.BLUE}Basic Text Source Directory', type=click.Path(exists=True), default=os.getcwd(),hide_input=False,show_choices=False,show_default=False,prompt_suffix=' <'+os.getcwd()+'> : ')
    if not SourceDir.endswith(os.sep):
        SourceDir = SourceDir + os.sep

    TargetDir = click.prompt(f'{Fore.BLUE}Target Directory', type=click.Path(exists=False), default=os.getcwd(),hide_input=False,show_choices=False,show_default=False,prompt_suffix=' <'+os.getcwd()+'> : ')
    if not TargetDir.endswith(os.sep):
        TargetDir = TargetDir + os.sep
        
    print(f'{Fore.GREEN}{Style.BRIGHT}\nWav File Parameters')
        
    ONES_FREQ = int(click.prompt(f'{Fore.YELLOW}Bit 1 Frequency Hz' ,default=str(ONES_FREQ), type=click.Choice(['300','500','600','800','1000','1200','2000','2400','4800','9600']),hide_input=False,show_choices=False,show_default=False,prompt_suffix=' <'+str(ONES_FREQ)+'> :'))
    ZERO_FREQ = int(click.prompt(f'{Fore.YELLOW}Bit 0 Frequency Hz' ,default=str(ZERO_FREQ), type=click.Choice(['300','500','600','800','1000','1200','2000','2400','4800','9600']),hide_input=False,show_choices=False,show_default=False,prompt_suffix=' <'+str(ZERO_FREQ)+'> :'))
    FRAMERATE = int(click.prompt(f'{Fore.YELLOW}Framerate Hz' ,default=str(FRAMERATE), type=click.Choice(['4800','9600','11025','22050','44100','48000']),hide_input=False,show_choices=False,show_default=False,prompt_suffix=' <'+str(FRAMERATE)+'> :'))
    AMPLITUDE = int(click.prompt(f'{Fore.YELLOW}Amplitude' ,default=str(AMPLITUDE), type=click.IntRange(0, 255),hide_input=False,show_default=False,prompt_suffix=' <'+str(AMPLITUDE)+'> :'))
    LEADER    = int(click.prompt(f'{Fore.YELLOW}Leader in seconds' ,default=str(LEADER),type=click.IntRange(0, 60),hide_input=False,show_default=False,prompt_suffix=' <'+str(LEADER)+'> :'))
    STARTBIT  = int(click.prompt(f'{Fore.YELLOW}Start Bit 0 or 1',default=str(STARTBIT),type=click.IntRange(0, 1),hide_input=False,show_default=False,prompt_suffix=' <'+str(STARTBIT)+'> :'))
    PARITY    = int(click.prompt(f'{Fore.YELLOW}Parity (0 Odd) or (1 Even)',default=str(PARITY),type=click.IntRange(0, 1),hide_input=False,show_default=False,prompt_suffix=' <'+str(PARITY)+'> :'))
    
    AlphaDir = click.confirm(f'{Fore.MAGENTA}\nDo you want to save files in alphabetized directories ?',default='Y')
        
    if click.confirm(f'{Fore.RED}\nProceed ?',default='Y'):
    
        for path in Path(SourceDir).glob('*.txt'):
            SourceFile=os.path.join(SourceDir, path)
            FileName=os.path.splitext(path.name)[0]
            AlphaName=FileName[0].upper()
            
            WavDir = os.path.join(TargetDir, 'wav')
            if not os.path.exists(WavDir):
                os.makedirs(WavDir)
            
            if (AlphaDir):
                WavDir=os.path.join(WavDir,AlphaName)
                if not os.path.exists(WavDir):
                        os.makedirs(WavDir)    
            
            TargetFile=os.path.join(WavDir, FileName+'.wav')
            
            Binary_Data=Create_BinData(SourceFile)
            FName=Path(TargetFile).resolve().stem
            
            print(f'{Fore.YELLOW}Creating File {TargetFile}')
            Write_Wav(TargetFile,Binary_Data)
            Write_Tag(TargetFile,FName)
    else:
        print(f'{Fore.RED}\nABORTED')