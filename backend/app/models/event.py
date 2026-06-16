from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class SportType(str, enum.Enum):
    marathon = "马拉松"
    cycling  = "骑行"
    trail    = "越野"
    other    = "其他"

class RegStatus(str, enum.Enum):
    open   = "报名中"
    closed = "已截止"
    soon   = "即将开始"

class Event(Base):
    __tablename__ = "events"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    title          = Column(String(200), nullable=False, comment="赛事名称")
    sport_type     = Column(Enum(SportType), nullable=False, comment="运动类型")
    province       = Column(String(50), comment="省份")
    city           = Column(String(50), comment="城市")
    event_date     = Column(Date, comment="比赛日期")
    reg_start_date = Column(Date, comment="报名开始日期")
    reg_end_date   = Column(Date, comment="报名截止日期")
    distances      = Column(String(200), comment="距离组别，逗号分隔，如42km,21km")
    official_url   = Column(String(500), comment="官网链接")
    image_url      = Column(String(500), comment="赛事图片")
    description    = Column(Text, comment="赛事描述")
    reg_status     = Column(Enum(RegStatus), default=RegStatus.open, comment="报名状态")
    source         = Column(String(100), comment="数据来源网站")
    source_id      = Column(String(200), unique=True, comment="来源网站的唯一ID，去重用")
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())