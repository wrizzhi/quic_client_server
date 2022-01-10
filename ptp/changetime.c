#include <stdio.h>
#include <time.h>

int main(int argc, char **argv)
{

  int result;
  struct timespec tp;
  clockid_t clk_id;

  clk_id = CLOCK_REALTIME;
//  clk_id = CLOCK_MONOTONIC;
//  clk_id = CLOCK_BOOTTIME;
//  clk_id = CLOCK_PROCESS_CPUTIME_ID;

  // int clock_gettime(clockid_t clk_id, struct timespec *tp);
  result = clock_gettime(clk_id, &tp);
  printf("result: %i\n", result);
  printf("tp.tv_sec: %ld\n", tp.tv_sec);
  printf("tp.tv_nsec: %ld\n", tp.tv_nsec);
  tp.tv_sec += 10;
  result = clock_settime(clk_id, &tp);
  printf("result: %i\n", result);
  result = clock_gettime(clk_id, &tp);
  printf("result: %i\n", result);
  printf("tp.tv_sec: %ld\n", tp.tv_sec);
  printf("tp.tv_nsec: %ld\n", tp.tv_nsec);

}