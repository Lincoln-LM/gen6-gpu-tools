struct mersenne_twister {
    uint state[624];
    uint index;
};

inline void mt_shuffle(struct mersenne_twister *rng) {
    rng->index = 0;
    for (int i = 0; i < 227; i++) {
        uint y = (rng->state[i] & 0x80000000) | (rng->state[i+1] & 0x7fffffff);
        rng->state[i] = rng->state[i + 397] ^ (y>>1) ^ (0x9908b0df * (y & 1));
    }
    for (int i = 227; i < 623; i++) {
        uint y = (rng->state[i] & 0x80000000) | (rng->state[i+1] & 0x7fffffff);
        rng->state[i] = rng->state[i - 227] ^ (y>>1) ^ (0x9908b0df * (y & 1));
    }
    uint y = (rng->state[623] & 0x80000000) | (rng->state[0] & 0x7fffffff);
    rng->state[623] ^= (y>>1) ^ (0x9908b0df * (y & 1));
}

inline void advance(struct mersenne_twister *rng, uint advances) {
    uint advance = advances + rng->index;
    while (advance >= 624) {
        mt_shuffle(rng);
        advance -= 624;
    }
    rng->index = advance;
}

inline uint next_uint(struct mersenne_twister *rng) {
    if (rng->index == 624) {
        mt_shuffle(rng);
    }
    uint y = rng->state[rng->index++];
    y ^= y >> 11;
    y ^= (y << 7) & 0x9d2c5680;
    y ^= (y << 15) & 0xefc60000;
    y ^= y >> 18;
    return y;
}

inline uchar next_32(struct mersenne_twister *rng) {
    return next_uint(rng) >> 27;
}

inline void init(struct mersenne_twister *rng, uint seed) {
    rng->index = 624;
    rng->state[0] = seed;
    for (uint i = 1; i < 624; i++) {
        seed = 0x6C078965 * (seed ^ (seed >> 30)) + i;
        rng->state[i] = seed;
    }
}

#ifndef MIN_ADVANCE
#define MIN_ADVANCE 0
#endif
#ifndef MAX_ADVANCE
#define MAX_ADVANCE 0
#endif
#ifndef IVS
#define IVS 0
#endif

__kernel void find_initial_seeds(const uint offset, __global uint *cnt, __global uint *res_g) {
    uint seed = get_global_id(0) + offset;
    struct mersenne_twister rng;
    init(&rng, seed);
    advance(&rng, MIN_ADVANCE);
    uint ivs = 0;
    ivs |= next_32(&rng);
    ivs <<= 5;
    ivs |= next_32(&rng);
    ivs <<= 5;
    ivs |= next_32(&rng);
    ivs <<= 5;
    ivs |= next_32(&rng);
    ivs <<= 5;
    ivs |= next_32(&rng);
    ivs <<= 5;
    ivs |= next_32(&rng);
    for (int adv = MIN_ADVANCE; adv < MAX_ADVANCE; adv++) {
        if ((ivs & 0x3fffffff) == IVS) {
            res_g[atomic_inc(&cnt[0])] = seed;
        }
        ivs <<= 5;
        ivs |= next_32(&rng);
    }
}
