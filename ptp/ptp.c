#include <arpa/inet.h>
#include <errno.h>
#include <inttypes.h>
#include <linux/errqueue.h>
#include <linux/net_tstamp.h>
#include <linux/sockios.h>
#include <net/if.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#define UDP_MAX_LENGTH 1500

typedef struct {
  int fd;
  int port;
  int err_no;
  struct sockaddr_in local;
  struct sockaddr_in remote;
  struct timeval time_kernel;
  struct timeval time_user;
  int64_t prev_serialnum;
} socket_info;

struct d_time {
        long   my_sec;        /* seconds */
        long   my_nsec;       /* nanoseconds */
        double act_sec;
}timing;

static int setup_udp_receiver(socket_info *inf, int port) {
  inf->port = port;
  inf->fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (inf->fd < 0) {
    inf->err_no = errno;
    fprintf(stderr, "setup_udp_server: socket failed: %s\n",
            strerror(inf->err_no));
    return inf->fd;
  }

  int timestampOn =
      SOF_TIMESTAMPING_RX_SOFTWARE | SOF_TIMESTAMPING_TX_SOFTWARE |
      SOF_TIMESTAMPING_SOFTWARE | SOF_TIMESTAMPING_RX_HARDWARE |
      SOF_TIMESTAMPING_TX_HARDWARE | SOF_TIMESTAMPING_RAW_HARDWARE |
      // SOF_TIMESTAMPING_OPT_TSONLY |
      0;
  int r = setsockopt(inf->fd, SOL_SOCKET, SO_TIMESTAMPING, &timestampOn,
                     sizeof timestampOn);
  if (r < 0) {
    inf->err_no = errno;
    fprintf(stderr, "setup_udp_server: setsockopt failed: %s\n",
            strerror(inf->err_no));
    return r;
  }

  int on = 1;
  r = setsockopt(inf->fd, SOL_SOCKET, SO_REUSEPORT, &on, sizeof on);
  if (r < 0) {
    inf->err_no = errno;
    fprintf(stderr, "setup_udp_server: setsockopt2 failed: %s\n",
            strerror(inf->err_no));
    return r;
  }

  inf->local = (struct sockaddr_in){.sin_family = AF_INET,
                                    .sin_port = htons((uint16_t)port),
                                    .sin_addr.s_addr = htonl(INADDR_ANY)};
  r = bind(inf->fd, (struct sockaddr *)&inf->local, sizeof inf->local);
  if (r < 0) {
    inf->err_no = errno;
    fprintf(stderr, "setup_udp_server: bind failed: %s\n",
            strerror(inf->err_no));
    return r;
  }

  inf->prev_serialnum = -1;

  return 0;
}

static int setup_udp_sender(socket_info *inf, int port, char *address) {
  inf->port = port;
  inf->fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (inf->fd < 0) {
    inf->err_no = errno;
    fprintf(stderr, "setup_udp_client: socket failed: %s\n",
            strerror(inf->err_no));
    return inf->fd;
  }

  int timestampOn =
      SOF_TIMESTAMPING_RX_SOFTWARE | SOF_TIMESTAMPING_TX_SOFTWARE |
      SOF_TIMESTAMPING_SOFTWARE | SOF_TIMESTAMPING_RX_HARDWARE |
      SOF_TIMESTAMPING_TX_HARDWARE | SOF_TIMESTAMPING_RAW_HARDWARE |
      // SOF_TIMESTAMPING_OPT_TSONLY |
      0;
  int r = setsockopt(inf->fd, SOL_SOCKET, SO_TIMESTAMPING, &timestampOn,
                     sizeof timestampOn);
  if (r < 0) {
    inf->err_no = errno;
    fprintf(stderr, "setup_udp_server: setsockopt failed: %s\n",
            strerror(inf->err_no));
    return r;
  }

  inf->remote = (struct sockaddr_in){.sin_family = AF_INET,
                                     .sin_port = htons((uint16_t)port)};
  r = inet_aton(address, &inf->remote.sin_addr);
  if (r == 0) {
    fprintf(stderr, "setup_udp_client: inet_aton failed\n");
    inf->err_no = 0;
    return -1;
  }

  inf->local = (struct sockaddr_in){.sin_family = AF_INET,
                                    .sin_port = htons(0),
                                    .sin_addr.s_addr = htonl(INADDR_ANY)};
  inf->prev_serialnum = -1;

  return 0;
}

static void handle_scm_timestamping(struct scm_timestamping *ts) {
  /*for (size_t i = 0; i < 1; i++) {
    printf("timestamp: %lld.%.9lds\n", (long long)ts->ts[i].tv_sec,
           ts->ts[i].tv_nsec);
  }*/
  timing.my_sec = ts->ts[0].tv_sec; 
  timing.my_nsec = ts->ts[0].tv_nsec;
}

static void handle_time(struct msghdr *msg) {

  for (struct cmsghdr *cmsg = CMSG_FIRSTHDR(msg); cmsg;
       cmsg = CMSG_NXTHDR(msg, cmsg)) {
    /*printf("level=%d, type=%d, len=%zu\n", cmsg->cmsg_level, cmsg->cmsg_type,
           cmsg->cmsg_len);*/

    if (cmsg->cmsg_level == SOL_IP && cmsg->cmsg_type == IP_RECVERR) {
      struct sock_extended_err *ext =
          (struct sock_extended_err *)CMSG_DATA(cmsg);
      //printf("errno=%d, origin=%d\n", ext->ee_errno, ext->ee_origin);
      continue;
    }

    if (cmsg->cmsg_level != SOL_SOCKET)
      continue;

    switch (cmsg->cmsg_type) {
    case SO_TIMESTAMPNS: {
      struct scm_timestamping *ts = (struct scm_timestamping *)CMSG_DATA(cmsg);
      handle_scm_timestamping(ts);
    } break;
    case SO_TIMESTAMPING: {
      struct scm_timestamping *ts = (struct scm_timestamping *)CMSG_DATA(cmsg);
      handle_scm_timestamping(ts);
    } break;
    default:
      /* Ignore other cmsg options */
      break;
    }
  }
  //printf("End messages\n");
}

static ssize_t udp_receive(socket_info *inf, char *buf, size_t len) {
  char ctrl[2048];
  struct iovec iov = (struct iovec){.iov_base = buf, .iov_len = len};
  struct msghdr msg = (struct msghdr){.msg_control = ctrl,
                                      .msg_controllen = sizeof ctrl,
                                      .msg_name = &inf->remote,
                                      .msg_namelen = sizeof inf->remote,
                                      .msg_iov = &iov,
                                      .msg_iovlen = 1};
  ssize_t recv_len = recvmsg(inf->fd, &msg, 0);
  gettimeofday(&inf->time_user, NULL);

  if (recv_len < 0) {
    inf->err_no = errno;
    fprintf(stderr, "udp_receive: recvfrom failed: %s\n",
            strerror(inf->err_no));
  }

  handle_time(&msg);

  return recv_len;
}

static ssize_t udp_send(socket_info *inf, char *buf, size_t len) {
  struct iovec iov = (struct iovec){.iov_base = buf, .iov_len = len};
  struct msghdr msg = (struct msghdr){.msg_name = &inf->remote,
                                      .msg_namelen = sizeof inf->remote,
                                      .msg_iov = &iov,
                                      .msg_iovlen = 1};
  gettimeofday(&inf->time_user, NULL);
  //printf("Sending %s\n",buf);

  ssize_t send_len = sendmsg(inf->fd, &msg, 0);
  if (send_len < 0) {
    inf->err_no = errno;
    fprintf(stderr, "udp_send: sendmsg failed: %s\n", strerror(inf->err_no));
  }

  return send_len;
}

static ssize_t meq_receive(socket_info *inf, char *buf, size_t len) {
  struct iovec iov = (struct iovec){.iov_base = buf, .iov_len = len};
  char ctrl[2048];
  struct msghdr msg = (struct msghdr){.msg_control = ctrl,
                                      .msg_controllen = sizeof ctrl,
                                      .msg_name = &inf->remote,
                                      .msg_namelen = sizeof inf->remote,
                                      .msg_iov = &iov,
                                      .msg_iovlen = 1};
  ssize_t recv_len = recvmsg(inf->fd, &msg, MSG_ERRQUEUE);
  if (recv_len < 0) {
    inf->err_no = errno;
    if (errno != EAGAIN) {
      fprintf(stderr, "meq_receive: recvmsg failed: %s\n",
              strerror(inf->err_no));
    }
    return recv_len;
  }
  handle_time(&msg);

  return recv_len;
}

typedef struct {
  int64_t serialnum;

  int64_t user_time_serialnum;
  int64_t user_time;

  int64_t kernel_time_serialnum;
  int64_t kernel_time;

  size_t message_bytes;
} message_header;

static const size_t payload_max = UDP_MAX_LENGTH - sizeof(message_header);

static void master_functions(char *host) {
  socket_info inf,inf2;
  int ret;
  int sender,reciever;
  char packet_buffer[4096];
  char str1[300];
  size_t len;
  sender = setup_udp_sender(&inf, 8000, host);
    if (sender < 0) {
        return;
    }
  reciever = setup_udp_receiver(&inf2, 8001);
    if (reciever < 0) {
        return;
     } 
  
  for (int i = 0; i < 10000; i++) {
    useconds_t t = random() % 2000000;
    
    //ret = setup_udp_sender(&inf, 8000, host);
 
    /*ssize_t len =
        generate_random_message(&inf, packet_buffer, sizeof packet_buffer);*/
    strcpy(packet_buffer,"SYNC MESSAGE");
    len = strlen(packet_buffer);
    if (len < 0) {
      return;
    }
    udp_send(&inf, packet_buffer, (size_t)len);
    printf("SYNC MESSAGE SENT\n");
    while (meq_receive(&inf, packet_buffer, sizeof packet_buffer) != -1) {
    }
    struct d_time first_save = timing; // T1 IS SAVED TO BE SENT IN THE FOLLOW UP MESSAGE
    sprintf(str1,"%ld.%.9ld",first_save.my_sec,first_save.my_nsec);
    strcpy(packet_buffer,str1);
    len = strlen(packet_buffer);
    if (len < 0) {
      return;
    }
    udp_send(&inf, packet_buffer, (size_t)len); // T1 IS SENT HERE
    printf("FOLLOW UP MESSAGE SENT WITH T1 = %s\n",str1);
    while (meq_receive(&inf, packet_buffer, sizeof packet_buffer) != -1) {
    }
    memset(packet_buffer,0,strlen(packet_buffer));
    udp_receive(&inf2, packet_buffer, sizeof packet_buffer);
    printf("here %s\n",packet_buffer);
    printf("DELAY REQUEST MESSAGE IS RECIEVED\n");
    struct d_time fourth_save = timing; //T4 IS CAPTURED HERE TO BE SENT IN THE NEXT MESSAGE
    memset(packet_buffer,0,strlen(packet_buffer));
    memset(str1,0,strlen(str1));
    sprintf(str1,"%ld.%.9ld",fourth_save.my_sec,fourth_save.my_nsec);
    //usleep(2e6);
    
    strcpy(packet_buffer,str1);
    len = strlen(packet_buffer);
     if (len < 0) {
      return;
    }
    udp_send(&inf, packet_buffer, (size_t)len);
    while (meq_receive(&inf, packet_buffer, sizeof packet_buffer) != -1) {
    }
    printf("DELAY RESPONSE MESSAGE IS SENT WITH T4 = %s\n",str1);
    sleep(2);
  }
}

static void slave_functions(char *host) {
  socket_info inf,inf2;
  size_t len;
  char packet_buffer[4096];
  int ret;
  int sender,reciever;
  long mpd_sec,mpd_nsec,offset_sec,offset_nsec;
  double mpd,offset;
  reciever = setup_udp_receiver(&inf, 8000);
    if (reciever < 0) {
        return;
    }
  sender = setup_udp_sender(&inf2, 8001,host);
    if (sender < 0) {
        return;
    }
  printf("T1,T2,T3,T4,T2-T1,T4-T3,MPD_S,OFF_S\n");
  //for (int i = 0; i < 1000; i++) {
  while (1) {
    mpd_sec = 0 ; mpd_nsec = 0 ; offset_sec = 0 ;offset_nsec = 0; mpd = 0;offset = 0;
    
    memset(packet_buffer,0,strlen(packet_buffer));
    udp_receive(&inf, packet_buffer, sizeof packet_buffer);
    //printf("here %s \n",packet_buffer);
    struct d_time second_save = timing; //T2 IS TAKEN FROM SLAVE AT RECEIPT OF SYNC MESSAGE
    //printf("Captured T2 is %ld.%.9ld",second_save.my_sec,second_save.my_nsec);
    memset(packet_buffer,0,strlen(packet_buffer));
    udp_receive(&inf, packet_buffer, sizeof packet_buffer); // T1 IS RECIEVED HERE
    //printf("here %s\n",packet_buffer);
    struct d_time first_save;
    first_save.my_sec = 0;
    first_save.my_nsec = 0;
    int val,i;
    char * token = strtok(packet_buffer, ".");
    val = atoi(token);
    first_save.my_sec = val;
    token = strtok(NULL,".");
    val = atoi(token);
    first_save.my_nsec = val;
    //printf("timestamp from follow up: %ld.%.9lds\n", first_save.my_sec,first_save.my_nsec)
    memset(packet_buffer,0,strlen(packet_buffer));
    strcpy(packet_buffer,"DELAY REQUEST MESSAGE"); // DELAY REQUEST IS SENT HERE T3 WILL BE SAVED HERE
    len = strlen(packet_buffer);
    if (len < 0) {
      return;
    }
    udp_send(&inf2, packet_buffer, (size_t)len);
    while (meq_receive(&inf2, packet_buffer, sizeof packet_buffer) != -1) {
    }
    struct d_time third_save = timing; //T3 IS SAVED HERE
    //reciever = setup_udp_receiver(&inf2, 8000);
    //printf("HERE1\n");
    //if (reciever < 0) {
    //    return;
    //}
    //printf("HERE2\n");
    memset(packet_buffer,0,strlen(packet_buffer));
    //printf("HERE3\n");
    udp_receive(&inf, packet_buffer, sizeof(packet_buffer));  //T4 IS RECIEVED HERE 
    //printf("here  \n");
    struct d_time fourth_save;
    fourth_save.my_sec = 0;
    fourth_save.my_nsec = 0;
    token = strtok(packet_buffer, ".");
    val = atoi(token);
    fourth_save.my_sec = val;
    token = strtok(NULL,".");
    val = atoi(token);
    fourth_save.my_nsec = val;
    printf("%ld.%.9lds,", first_save.my_sec,first_save.my_nsec);
    printf("%ld.%.9lds,",second_save.my_sec,second_save.my_nsec);
    printf("%ld.%.9lds,", third_save.my_sec,third_save.my_nsec);
    printf("%ld.%.9lds,", fourth_save.my_sec,fourth_save.my_nsec);
    first_save.act_sec = first_save.my_sec + first_save.my_nsec*1e-9;
    second_save.act_sec = second_save.my_sec + second_save.my_nsec*1e-9;
    third_save.act_sec = third_save.my_sec + third_save.my_nsec*1e-9;
    fourth_save.act_sec = fourth_save.my_sec + fourth_save.my_nsec*1e-9;
    mpd = ((second_save.act_sec - first_save.act_sec) - (fourth_save.act_sec - third_save.act_sec))/2;
    offset =  second_save.act_sec - first_save.act_sec - mpd;
    printf("%fs,",second_save.act_sec - first_save.act_sec);
    printf("%fs,",fourth_save.act_sec - third_save.act_sec);
    printf("%fs,",mpd);
    printf("%fs\n",offset);
    //printf("done\n");
    sleep(1);
  }
}


#define USAGE "Usage: %s [-s master ip | -m slave ip]\n"

int main(int argc, char *argv[]) {
  if (argc < 2) {
    fprintf(stderr, USAGE, argv[0]);
    return 0;
  }

  if (0 == strcmp(argv[1], "-m")) {
    if (argc < 3) {
      fprintf(stderr, USAGE, argv[0]);
      return 0;
    }
    master_functions(argv[2]);
  } else if (0 == strcmp(argv[1], "-s")) {
    if (argc < 3) {
      fprintf(stderr, USAGE, argv[0]);
      return 0;
    }
    slave_functions(argv[2]);
  } else {
    fprintf(stderr, USAGE, argv[0]);
  }
}
