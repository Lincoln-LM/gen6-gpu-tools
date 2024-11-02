#ifndef BLINK_COUNT
#define BLINK_COUNT 0
#endif
#ifndef BLINK_DATA
#define BLINK_DATA
#endif
#ifndef BASE_ADVANCE
#define BASE_ADVANCE 0
#endif
#ifndef MAX_ADVANCE
#define MAX_ADVANCE 0
#endif
#ifndef LEEWAY
#define LEEWAY 0
#endif
__constant short BLINKS[BLINK_COUNT] = { BLINK_DATA };

struct tinymt {
  uint state[4];
};

inline void advance(struct tinymt *rng) {
  uint y = rng->state[3];
  uint x = (rng->state[0] & 0x7FFFFFFF) ^ rng->state[1] ^ rng->state[2];
  x ^= x << 1;
  y ^= (y >> 1) ^ x;

  rng->state[0] = rng->state[1];
  rng->state[1] = rng->state[2] ^ ((y & 1) * 0x8F7011EE);
  rng->state[2] = x ^ ((y << 10) & 0xFFFFFFFF) ^ ((y & 1) * 0xFC78FF1F);
  rng->state[3] = y;
}

inline uint next_uint(struct tinymt *rng) {
  advance(rng);
  uint t0 = rng->state[3];
  uint t1 = rng->state[0] + (rng->state[2] >> 8);
  t0 ^= t1;
  if (t1 & 1) {
    t0 ^= 0x3793FDFF;
  }
  return t0;
}

inline uint next_blink(struct tinymt *rng) {
  return (((unsigned long)next_uint(rng)) * 240) >> 32;
}

inline void init(struct tinymt *rng, unsigned int seed) {
  rng->state[0] = seed;
  rng->state[1] = 0x8F7011EE;
  rng->state[2] = 0xFC78FF1F;
  rng->state[3] = 0x3793FDFF;

  for (int i = 1; i < 8; i++) {
    rng->state[i & 3] ^= (0x6C078965 * (rng->state[(i - 1) & 3] ^ (rng->state[(i - 1) & 3] >> 30)) + i);
  }

  for (int i = 0; i < 8; i++) {
    advance(rng);
  }
}

__kernel void find_initial_seeds(const uint offset, __global uint *cnt, __global uint *res_g) {
  unsigned int seed = get_global_id(0) | ((get_global_id(1) + offset) << 16);
  struct tinymt rng;
  init(&rng, seed);
  for (int i = 0; i < BASE_ADVANCE; i++) {
    advance(&rng);
  }

  for (int start = BASE_ADVANCE; start <= MAX_ADVANCE; start++) {
    bool valid = true;
    struct tinymt test_rng;
    test_rng.state[0] = rng.state[0];
    test_rng.state[1] = rng.state[1];
    test_rng.state[2] = rng.state[2];
    test_rng.state[3] = rng.state[3];
    next_uint(&rng);
    // TODO: better checking algorithm
    for (int i = 0; i < BLINK_COUNT; i++) {
      short blink = next_blink(&test_rng);
      valid = (BLINKS[i] - LEEWAY) <= blink && blink <= (BLINKS[i] + LEEWAY);
      if (!valid) {
        break;
      }
    }
    if (valid) {
      res_g[atomic_inc(&cnt[0])] = seed;
      break;
    }
  }
}