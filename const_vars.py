######################################################
## only constant var can be defined in this file
######################################################


NULL_CHAR  = '\x00'

COMMAND_AREA_SIZE = 0X100

#Send Download mode to board's RAM loader
USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE = 0x50000210

FLASH_DEV_TYPE_IS_NOR = 0x01
FLASH_DEV_TYPE_IS_NAND = 0x02

MAGIC_WORD = '\xde\xad\xbe\xef'
BL_MAGIC_STRING = "InfoMax Communication"

##### usb read

USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET = 0x00000004
USB_PROGRAMMER_CHK_ERASE_RDY_CMD_OFFSET = 0x00000005
USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET = 0x00000006
USB_PROGRAMMER_GET_DEV_TYPE_OFFSET = 0x00000007
USB_PROGRAMMER_GET_IMG_ADDR_BY_ID = 0x00000011
USB_PROGRAMMER_GET_NAND_SPARE_DATA = 0x00000012

# Option for 'USB_PROGRAMMER_SET_BOOT_DEVICE' command 
# download code to flash directory
DOWNLOAD_TYPE_FLASH = 1
# download second boot loader to RAM
DOWNLOAD_TYPE_RAM   = 2

FLASH_BASE_ADDR                 = 0x10000000
IM9828_RAM_BOOT_BASE_ADDR       = 0x1FFE0000
RAM_BOOT_BASE_ADDR              = IM9828_RAM_BOOT_BASE_ADDR


##### usb write
##USB_PROGRAMMER_SET_PROG_MODE_CMD = 0x50000100

# 0015, command to tell BB which address is going to be programmed.
##USB_PROGRAMMER_SET_PROG_ADDR_CMD = 0x50000104
# Command to tell Magic that the image boot from RAM or FLASH
USB_PROGRAMMER_SET_BOOT_DEVICE = 0x50000200
# Command to tell Magic that the image boot from which address
USB_PROGRAMMER_SET_BOOT_ADDR = 0x50000204
# PC will check the burned image and tell us the status
USB_PROGRAMMER_SET_VERIFICATION_STATUS = 0x50000208

USB_PROGRAMMER_WRITE_BOOT_PARAMETERS = 0x5000020C
# Send Download mode to board's RAM loader
USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE = 0x50000210
# PC will set whether enable to write spare data
USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL = 0x50000300
# PC will set whether enable to write spare data
USB_PROGRAMMER_ERASE_NAND_CMD = 0x50000301
# PC will write spare date through this command
USB_PROGRAMMER_WR_NAND_SPARE_DATA = 0x50000302
# PC will set the partition start addrss
# and data length in the partition through this command
USB_PROGRAMMER_SET_NAND_PARTITION_INFO = 0x50000303

USB_PROGRAMMER_WR_BB_REG         = 0x50000400
USB_PROGRAMMER_FINISH_MAGIC_WORD = 0x5a5a5a5a

# WmDropFiles
CFG_IM9828_NUCLEUS = True
CFG_IM9828_ECOS = True

NAND_BLOCK_SIZE      = 0x10000
SECTOR_SIZE          = 0x200                    # 512 
SIZE_PER_WRITE       = NAND_BLOCK_SIZE
SIZE_PER_READ        = NAND_BLOCK_SIZE
SECTOR_NUM_PER_OP    = NAND_BLOCK_SIZE/SECTOR_SIZE                     # 128 
SECTOR_NUM_PER_WRITE = SECTOR_NUM_PER_OP        # 128 
SECTOR_NUM_PER_READ  = SECTOR_NUM_PER_OP        # 128 


# Erase  size 
CFG_MAX_ERASE_SIZE = True
NAND_ERASE_MAX_LEN_PER_TIME = 0x08000000
NAND_ERASE_MIN_LEN_PER_TIME = 0x00200000 # MData: 2M 


SIZE_YAFFS2_HEADER = 16
YAFFS2_MAGIC_HEAD_ID = 0x4F464E49
YAFFS2_VERSION_512   = 0x00
YAFFS2_VERSION_2048  = 0x01
YAFFS2_CHUNKSIZE_2K  = 2048
YAFFS2_SPARESIZE_2K  = 64
YAFFS2_VERSION_4096  = 0x02
YAFFS2_CHUNKSIZE_4K  = 4096
YAFFS2_SPARESIZE_4K  = 128


#enum NAND_IMG_Type
RAWDATA        = 0x0
YAFFS2        = 0x1
DYN_ID        = 0x2


# Dyn ID 
ID_NULL                         = 99
#enum DYN_ID_Type
ID_BAREBOX                      = 0x0
ID_BAREBOX_ENV                  = 0x1
ID_LDR_APP                      = 0x2
ID_IMEI                         = 0x3
ID_ICON                         = 0x4

# 1228 Two Stage Download Type
#enum TWO_STAGE_DL_Type
TWO_STAGE_ZERO_OP               = 0x0
TWO_STAGE_SINGLE                = 0x1
TWO_STAGE_PACKAGE               = 0x2
TWO_STAGE_IMEI                  = 0x3
TWO_STAGE_ERASE                 = 0x4
TWO_STAGE_DUMP                  = 0x5

#enum IMEI_SN_Type
IMEISN_IMEI1                    = 0x1
IMEISN_SN                       = 0x2
IMEISN_IMEI_SV                  = 0x3
IMEISN_ID                       = 0x4
IMEISN_IMEI2                    = 0x5
IMEISN_BTMAC                    = 0x6


# magic word for extract bsp pkg
PACKAGE_HEADER_MAGIC_PATTERN = "(^_^)y :-)(^~~^)"
PACKAGE_HEADER_PLATFORM      = "iM9828"
PACKAGE_TAIL_MAGIC_PATTERN   = "(^~~^)(-: y(^_^)"
PACKAGE_TAIL_PLATFORM        = "im98xx"

# 1228 Program Image Type
#enum PROG_IMG_Type
IMG_BAREBOX        = 0x1
IMG_LDR_APP        = 0x2
IMG_MODEM          = 0x3
IMG_BOOTIMG        = 0x4
IMG_RECOVERY       = 0x5
IMG_SYSTEM         = 0x6
IMG_M_DATA         = 0x7
IMG_USER_DATA      = 0x8
IMG_IMEI           = 0x9
IMG_BAREBOX_ENV    = 0xA
IMG_ICON           = 0xB
IMG_MAX            = 0xC
IMG_CACHE          = 0xD   # not used
PROG_M_NUM = (IMG_MAX-1)

img_type_dict = {
    IMG_BAREBOX     : [ "IMG_BAREBOX", 'b' ],
    IMG_LDR_APP     : [ "IMG_LDR_APP", 'R' ],
    IMG_MODEM       : [ "IMG_MODEM", 'm' ],
    IMG_BOOTIMG     : [ "IMG_BOOTIMG", 'B' ],
    IMG_RECOVERY    : [ "IMG_RECOVERY", 'r' ],
    IMG_SYSTEM      : [ "IMG_SYSTEM", 's' ],
    IMG_M_DATA      : [ "IMG_M_DATA", 'M' ],
    IMG_USER_DATA   : [ "IMG_USER_DATA", 'u' ],
    IMG_IMEI        : [ "IMG_IMEI", 'i' ],
    IMG_BAREBOX_ENV : [ "IMG_BAREBOX_ENV", 'd' ],
    IMG_ICON        : [ "IMG_ICON", 'c' ],
    IMG_MAX         : [ "IMG_MAX", 'xxxx' ],
}



#  To make sure user version is ready to download 
#userModeOfDownloader = 0  #temp val, set randomly by me

