from elasticsearch import AsyncElasticsearch
from app.core.config import settings

es_client = AsyncElasticsearch(
    hosts=[settings.ES_HOST],
    basic_auth=(settings.ES_USERNAME, settings.ES_PASSWORD) if settings.ES_USERNAME else None,
    verify_certs=False,
    ssl_show_warn=False,
    request_timeout=30,
    # 关闭启动时的嗅探，避免初始化报错
    sniff_on_start=False,
    sniff_on_node_failure=False,
)

EVENT_INDEX = "movemark_events"

EVENT_MAPPING = {
    "mappings": {
        "properties": {
            "id":             {"type": "integer"},
            "title":          {"type": "text", "analyzer": "standard"},
            "sport_type":     {"type": "keyword"},
            "province":       {"type": "keyword"},
            "city":           {"type": "keyword"},
            "event_date":     {"type": "date"},
            "reg_end_date":   {"type": "date"},
            "reg_status":     {"type": "keyword"},
            "distances":      {"type": "text"},
            "description":    {"type": "text", "analyzer": "standard"},
            "official_url":   {"type": "keyword", "index": False},
            "image_url":      {"type": "keyword", "index": False},
            "source":         {"type": "keyword"},
            "source_id":      {"type": "keyword"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    }
}

async def init_es_index():
    """初始化ES索引（如果不存在则创建）"""
    try:
        exists = await es_client.indices.exists(index=EVENT_INDEX)
        if not exists:
            await es_client.indices.create(
                index=EVENT_INDEX,
                mappings=EVENT_MAPPING["mappings"],
                settings=EVENT_MAPPING["settings"],
            )
            print(f"ES索引 {EVENT_INDEX} 创建成功")
        else:
            print(f"ES索引 {EVENT_INDEX} 已存在")
    except Exception as e:
        print(f"ES索引初始化失败: {e}")
        raise