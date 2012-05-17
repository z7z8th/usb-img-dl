#include <sys/ioctl.h>
#include <stdio.h>
#include <stdlib.h>
#include <memory.h>
#include <scsi/scsi.h>
#include <scsi/sg.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#define READ_CAPACITY_COMMAND_LEN 10
#define READ_CAPACITY_REPLY_LEN   8

int
main(int argc, char *argv[])
{
  int fd, i;
  /* READ_CAPACITY command block */
  unsigned char READ_CAPACITY_CmdBlk[READ_CAPACITY_COMMAND_LEN]=
                              {READ_CAPACITY, 0,0,0,0,0,0,0,0,0};
  sg_io_hdr_t sg_io;
  unsigned char rd_cap_buff[READ_CAPACITY_REPLY_LEN];
  unsigned int lastblock, blocksize;
  unsigned long long disk_cap;
  unsigned char sense_buf[32];

  /* Open the sg device */
  if ((fd = open("/dev/sg2", O_RDONLY)) < 0) {
      perror("open sg");
      exit(1);
  }

  /* Initialize */
  memset(&sg_io, 0, sizeof(sg_io_hdr_t));

  /* Command block address and length */
  sg_io.cmdp = READ_CAPACITY_CmdBlk;
  sg_io.cmd_len = READ_CAPACITY_COMMAND_LEN;

  /* Response buffer address and length */
  sg_io.dxferp = rd_cap_buff;
  sg_io.dxfer_len = READ_CAPACITY_REPLY_LEN;

  /* Sense buffer address and length */
  sg_io.sbp = sense_buf;
  sg_io.mx_sb_len = sizeof(sense_buf);
  /* Control information */
  sg_io.interface_id = 'S';
  sg_io.dxfer_direction = SG_DXFER_FROM_DEV;
  sg_io.timeout = 10000; /* 10 seconds */

  /* Issue the SG_IO ioctl */
  if (ioctl(fd, SG_IO, &sg_io) < 0) {
    perror("ioctl SG_IO");
    exit(1);
  }

  /* Obtain results */
  if ((sg_io.info & SG_INFO_OK_MASK) == SG_INFO_OK) {
    /* Address of last disk block */
    lastblock =  ((rd_cap_buff[0]<<24)|(rd_cap_buff[1]<<16)|
              (rd_cap_buff[2]<<8)|(rd_cap_buff[3]));

    /* Block size */
    blocksize =  ((rd_cap_buff[4]<<24)|(rd_cap_buff[5]<<16)|
              (rd_cap_buff[6]<<8)|(rd_cap_buff[7]));

    /* Calculate disk capacity */
    disk_cap  = (lastblock+1);
    disk_cap *= blocksize;
    printf("Disk Capacity = %llu Bytes\n", disk_cap);

  }
  else
  {
      printf("ioctl SG_INFO wrong\n");
  }
  close(fd);
}

