import hashlib
import redis.asyncio as aioredis
from app.core.config import settings


class BloomFilter:
    """
    基于 Redis BitMap 的布隆过滤器

    原理：用多个哈希函数把元素映射到位数组的多个位置
    - 插入：把所有对应位置置1
    - 查询：检查所有对应位置是否全为1
    - 特点：有误判（假阳性），但无漏判，且空间极省
    """

    def __init__(self, redis_key: str, capacity: int = 1_000_000, error_rate: float = 0.01):
        """
        redis_key:  存储在Redis中的key名
        capacity:   预期最大元素数量
        error_rate: 允许的误判率（0.01 = 1%）
        """
        self.key = redis_key
        self.capacity = capacity
        self.error_rate = error_rate

        # 根据容量和误判率，计算最优参数
        # 位数组大小：m = -n*ln(p) / (ln2)^2
        import math
        self.bit_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        # 哈希函数个数：k = m/n * ln2
        self.hash_count = int((self.bit_size / capacity) * math.log(2))

        print(f"布隆过滤器初始化: key={redis_key}, 位数组={self.bit_size}, 哈希函数={self.hash_count}个")

    def _get_bit_positions(self, value: str) -> list[int]:
        """用不同的seed生成多个哈希值，对应位数组中的多个位置"""
        positions = []
        for i in range(self.hash_count):
            # 用 sha256 + seed 模拟多个哈希函数
            hash_val = hashlib.sha256(f"{i}:{value}".encode()).hexdigest()
            position = int(hash_val, 16) % self.bit_size
            positions.append(position)
        return positions

    async def add(self, value: str, redis_client) -> None:
        """将元素加入布隆过滤器"""
        positions = self._get_bit_positions(value)
        pipe = redis_client.pipeline()
        for pos in positions:
            pipe.setbit(self.key, pos, 1)
        await pipe.execute()

    async def exists(self, value: str, redis_client) -> bool:
        """检查元素是否（可能）存在"""
        positions = self._get_bit_positions(value)
        pipe = redis_client.pipeline()
        for pos in positions:
            pipe.getbit(self.key, pos)
        results = await pipe.execute()
        # 所有位都是1，才认为"存在"
        return all(results)

    async def add_batch(self, values: list[str], redis_client) -> None:
        """批量添加"""
        pipe = redis_client.pipeline()
        for value in values:
            for pos in self._get_bit_positions(value):
                pipe.setbit(self.key, pos, 1)
        await pipe.execute()


# 预定义两个过滤器实例
crawler_bloom = BloomFilter(
    redis_key="bloom:crawler:source_ids",
    capacity=500_000,  # 预期50万条爬虫数据
    error_rate=0.01,
)

event_id_bloom = BloomFilter(
    redis_key="bloom:events:ids",
    capacity=500_000,
    error_rate=0.001,  # 缓存穿透场景误判率更低
)