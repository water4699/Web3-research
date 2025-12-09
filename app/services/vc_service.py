"""
VC/机构服务 - 整合 RootData 抓取和数据库操作
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import VC
from app.services.rootdata_client import RootDataClient


class VCService:
    def __init__(self, db: Session):
        self.db = db
        self.rootdata = RootDataClient()

    async def fetch_and_save_vc(
        self,
        org_id: int,
        include_team: bool = True,
        include_investments: bool = True
    ) -> VC:
        """
        抓取VC/机构信息并保存到数据库
        """
        # 从 RootData 获取数据
        data = await self.rootdata.get_vc(
            org_id=org_id,
            include_team=include_team,
            include_investments=include_investments
        )

        # 检查是否已存在
        existing = self.db.query(VC).filter(VC.org_id == org_id).first()

        if existing:
            vc = existing
        else:
            vc = VC(org_id=org_id)
            self.db.add(vc)

        # 填充字段
        vc.org_name = data.get("org_name")
        vc.logo = data.get("logo")
        vc.rootdataurl = data.get("rootdataurl")
        vc.establishment_date = data.get("establishment_date")
        vc.description = data.get("description")
        vc.active = data.get("active", True)
        vc.category = data.get("category")
        vc.social_media = data.get("social_media")
        vc.investments = data.get("investments")
        vc.team_members = data.get("team_members")

        # X数据 (PRO)
        vc.heat = data.get("heat")
        vc.heat_rank = data.get("heat_rank")
        vc.influence = data.get("influence")
        vc.influence_rank = data.get("influence_rank")
        vc.followers = data.get("followers")
        vc.following = data.get("following")

        # 保存原始JSON
        vc.raw_json = data
        vc.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(vc)

        return vc

    async def fetch_and_save_investor_batches(
        self,
        page: int = 1,
        page_size: int = 10
    ) -> List[VC]:
        """
        批量抓取投资者信息并保存到数据库
        """
        data = await self.rootdata.get_investor_batches(page=page, page_size=page_size)
        items = data.get("items", [])
        vcs = []

        for item in items:
            org_id = item.get("invest_id")
            if not org_id:
                continue

            # 检查是否已存在
            existing = self.db.query(VC).filter(VC.org_id == org_id).first()

            if existing:
                vc = existing
            else:
                vc = VC(org_id=org_id)
                self.db.add(vc)

            # 填充字段
            vc.org_name = item.get("invest_name")
            vc.logo = item.get("logo")
            vc.description = item.get("description")
            vc.establishment_date = item.get("establishment_date")
            vc.investments = item.get("investments")
            vc.team_members = item.get("team_members")

            # 投资统计字段
            vc.invest_overview = item.get("invest_overview")
            vc.invest_range = item.get("invest_range")
            vc.invest_stics = item.get("invest_stics")
            vc.area = item.get("area")
            vc.last_fac_date = item.get("last_fac_date")
            vc.last_invest_num = item.get("last_invest_num")

            vc.raw_json = item
            vc.updated_at = datetime.utcnow()

            vcs.append(vc)

        self.db.commit()
        return vcs

    async def batch_fetch_vcs(self, org_ids: List[int]) -> List[VC]:
        """批量抓取VC"""
        vcs = []
        for org_id in org_ids:
            try:
                vc = await self.fetch_and_save_vc(org_id)
                vcs.append(vc)
            except Exception as e:
                print(f"Failed to fetch VC {org_id}: {e}")
        return vcs

    def get_vc(self, vc_id: int) -> Optional[VC]:
        """从数据库获取VC"""
        return self.db.query(VC).filter(VC.id == vc_id).first()

    def get_vc_by_org_id(self, org_id: int) -> Optional[VC]:
        """通过RootData org_id获取VC"""
        return self.db.query(VC).filter(VC.org_id == org_id).first()

    def list_vcs(self, skip: int = 0, limit: int = 100) -> List[VC]:
        """列出数据库中的VC"""
        return self.db.query(VC).offset(skip).limit(limit).all()

    def get_vc_as_dict(self, vc: VC) -> Dict:
        """将VC转换为字典"""
        return {
            "id": vc.id,
            "org_id": vc.org_id,
            "org_name": vc.org_name,
            "logo": vc.logo,
            "rootdataurl": vc.rootdataurl,
            "description": vc.description,
            "category": vc.category,
            "investments": vc.investments,
            "invest_overview": vc.invest_overview,
            "created_at": vc.created_at.isoformat() if vc.created_at else None,
            "updated_at": vc.updated_at.isoformat() if vc.updated_at else None
        }
