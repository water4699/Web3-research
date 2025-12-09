"""
通用数据服务 - 处理 FundingRound, Ecosystem, Tag, XData 的存储
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import FundingRound, Ecosystem, Tag, XData
from app.services.rootdata_client import RootDataClient


class DataService:
    def __init__(self, db: Session):
        self.db = db
        self.rootdata = RootDataClient()

    # ==================== 投资轮次 ====================

    async def fetch_and_save_funding_rounds(
        self,
        page: int = 1,
        page_size: int = 10,
        start_time: str = None,
        end_time: str = None,
        min_amount: int = None,
        max_amount: int = None,
        project_id: int = None
    ) -> List[FundingRound]:
        """
        批量获取投资轮次并保存到数据库
        """
        data = await self.rootdata.get_funding_rounds(
            page=page,
            page_size=page_size,
            start_time=start_time,
            end_time=end_time,
            min_amount=min_amount,
            max_amount=max_amount,
            project_id=project_id
        )

        items = data.get("items", [])
        rounds = []

        for item in items:
            # 创建新记录（投资轮次不做去重，可能有多轮）
            funding_round = FundingRound(
                project_id=item.get("project_id"),
                project_name=item.get("name"),
                logo=item.get("logo"),
                rounds=item.get("rounds"),
                published_time=item.get("published_time"),
                amount=item.get("amount"),
                valuation=item.get("valuation"),
                invests=item.get("invests"),
                raw_json=item
            )
            self.db.add(funding_round)
            rounds.append(funding_round)

        self.db.commit()
        return rounds

    def list_funding_rounds(
        self,
        skip: int = 0,
        limit: int = 100,
        project_id: int = None
    ) -> List[FundingRound]:
        """列出投资轮次"""
        query = self.db.query(FundingRound)
        if project_id:
            query = query.filter(FundingRound.project_id == project_id)
        return query.offset(skip).limit(limit).all()

    def get_funding_round_as_dict(self, fr: FundingRound) -> Dict:
        """将投资轮次转换为字典"""
        return {
            "id": fr.id,
            "project_id": fr.project_id,
            "project_name": fr.project_name,
            "logo": fr.logo,
            "rounds": fr.rounds,
            "published_time": fr.published_time,
            "amount": float(fr.amount) if fr.amount else None,
            "valuation": float(fr.valuation) if fr.valuation else None,
            "invests": fr.invests,
            "created_at": fr.created_at.isoformat() if fr.created_at else None
        }

    # ==================== 生态 ====================

    async def fetch_and_save_ecosystems(self) -> List[Ecosystem]:
        """
        获取生态列表并保存到数据库
        """
        data = await self.rootdata.get_ecosystem_map()
        ecosystems = []

        for item in data:
            ecosystem_id = item.get("ecosystem_id")
            if not ecosystem_id:
                continue

            # 检查是否已存在
            existing = self.db.query(Ecosystem).filter(
                Ecosystem.ecosystem_id == ecosystem_id
            ).first()

            if existing:
                eco = existing
            else:
                eco = Ecosystem(ecosystem_id=ecosystem_id)
                self.db.add(eco)

            eco.ecosystem_name = item.get("ecosystem_name")
            eco.project_num = item.get("project_num")
            eco.updated_at = datetime.utcnow()

            ecosystems.append(eco)

        self.db.commit()
        return ecosystems

    def list_ecosystems(self, skip: int = 0, limit: int = 100) -> List[Ecosystem]:
        """列出生态"""
        return self.db.query(Ecosystem).offset(skip).limit(limit).all()

    def get_ecosystem_as_dict(self, eco: Ecosystem) -> Dict:
        """将生态转换为字典"""
        return {
            "id": eco.id,
            "ecosystem_id": eco.ecosystem_id,
            "ecosystem_name": eco.ecosystem_name,
            "project_num": eco.project_num,
            "created_at": eco.created_at.isoformat() if eco.created_at else None,
            "updated_at": eco.updated_at.isoformat() if eco.updated_at else None
        }

    # ==================== 标签 ====================

    async def fetch_and_save_tags(self) -> List[Tag]:
        """
        获取标签列表并保存到数据库
        """
        data = await self.rootdata.get_tag_map()
        tags = []

        for item in data:
            tag_id = item.get("tag_id")
            if not tag_id:
                continue

            # 检查是否已存在
            existing = self.db.query(Tag).filter(Tag.tag_id == tag_id).first()

            if existing:
                tag = existing
            else:
                tag = Tag(tag_id=tag_id)
                self.db.add(tag)

            tag.tag_name = item.get("tag_name")
            tag.updated_at = datetime.utcnow()

            tags.append(tag)

        self.db.commit()
        return tags

    def list_tags(self, skip: int = 0, limit: int = 100) -> List[Tag]:
        """列出标签"""
        return self.db.query(Tag).offset(skip).limit(limit).all()

    def get_tag_as_dict(self, tag: Tag) -> Dict:
        """将标签转换为字典"""
        return {
            "id": tag.id,
            "tag_id": tag.tag_id,
            "tag_name": tag.tag_name,
            "created_at": tag.created_at.isoformat() if tag.created_at else None,
            "updated_at": tag.updated_at.isoformat() if tag.updated_at else None
        }

    # ==================== X数据 ====================

    async def fetch_and_save_x_data(self, entity_type: int) -> List[XData]:
        """
        批量获取X数据并保存到数据库
        entity_type: 1=项目, 2=机构, 3=人物
        """
        data = await self.rootdata.get_x_data_batches(entity_type)
        x_data_list = []

        for item in data:
            entity_id = item.get("id")
            if not entity_id:
                continue

            # 检查是否已存在
            existing = self.db.query(XData).filter(
                XData.entity_id == entity_id,
                XData.entity_type == entity_type
            ).first()

            if existing:
                x_data = existing
            else:
                x_data = XData(entity_id=entity_id, entity_type=entity_type)
                self.db.add(x_data)

            x_data.name = item.get("name")
            x_data.x = item.get("X")
            x_data.followers = item.get("followers")
            x_data.following = item.get("following")
            x_data.heat = item.get("heat")
            x_data.influence = item.get("influence")
            x_data.updated_at = datetime.utcnow()

            x_data_list.append(x_data)

        self.db.commit()
        return x_data_list

    async def fetch_hot_projects_on_x(
        self,
        heat: bool = True,
        influence: bool = True,
        followers: bool = True
    ) -> Dict:
        """
        获取X热门项目
        """
        return await self.rootdata.get_hot_projects_on_x(
            heat=heat,
            influence=influence,
            followers=followers
        )

    def list_x_data(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_type: int = None
    ) -> List[XData]:
        """列出X数据"""
        query = self.db.query(XData)
        if entity_type:
            query = query.filter(XData.entity_type == entity_type)
        return query.offset(skip).limit(limit).all()

    def get_x_data_as_dict(self, x_data: XData) -> Dict:
        """将X数据转换为字典"""
        return {
            "id": x_data.id,
            "entity_id": x_data.entity_id,
            "entity_type": x_data.entity_type,
            "name": x_data.name,
            "x": x_data.x,
            "followers": x_data.followers,
            "following": x_data.following,
            "heat": x_data.heat,
            "influence": x_data.influence,
            "created_at": x_data.created_at.isoformat() if x_data.created_at else None,
            "updated_at": x_data.updated_at.isoformat() if x_data.updated_at else None
        }

    # ==================== 同步更新 ====================

    async def get_sync_updates(
        self,
        begin_time: int,
        end_time: int = None
    ) -> List[Dict]:
        """
        获取数据更新列表
        """
        return await self.rootdata.get_sync_updates(
            begin_time=begin_time,
            end_time=end_time
        )
