"""
人物服务 - 整合 RootData 抓取和数据库操作
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import People
from app.services.rootdata_client import RootDataClient


class PeopleService:
    def __init__(self, db: Session):
        self.db = db
        self.rootdata = RootDataClient()

    async def fetch_and_save_people(self, people_id: int) -> People:
        """
        抓取人物信息并保存到数据库
        """
        # 从 RootData 获取数据
        data = await self.rootdata.get_people(people_id)

        # 检查是否已存在
        existing = self.db.query(People).filter(People.people_id == people_id).first()

        if existing:
            person = existing
        else:
            person = People(people_id=people_id)
            self.db.add(person)

        # 填充字段
        person.people_name = data.get("people_name")
        person.head_img = data.get("head_img")
        person.one_liner = data.get("one_liner")
        person.introduce = data.get("introduce")
        person.x = data.get("X")
        person.linkedin = data.get("linkedin")

        # X数据 (PRO)
        person.heat = data.get("heat")
        person.heat_rank = data.get("heat_rank")
        person.influence = data.get("influence")
        person.influence_rank = data.get("influence_rank")
        person.followers = data.get("followers")
        person.following = data.get("following")

        # 保存原始JSON
        person.raw_json = data
        person.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(person)

        return person

    async def fetch_hot_people_on_x(
        self,
        heat: bool = True,
        influence: bool = True,
        followers: bool = True
    ) -> Dict:
        """
        获取X热门人物
        """
        data = await self.rootdata.get_hot_people_on_x(
            heat=heat,
            influence=influence,
            followers=followers
        )
        return data

    async def fetch_and_save_job_changes(
        self,
        recent_joinees: bool = True,
        recent_resignations: bool = True
    ) -> Dict[str, List[People]]:
        """
        获取人物职位变动并保存到数据库
        """
        data = await self.rootdata.get_job_changes(
            recent_joinees=recent_joinees,
            recent_resignations=recent_resignations
        )

        result = {"recent_joinees": [], "recent_resignations": []}

        # 处理最近入职
        for item in data.get("recent_joinees", []):
            people_id = item.get("people_id")
            if not people_id:
                continue

            existing = self.db.query(People).filter(People.people_id == people_id).first()

            if existing:
                person = existing
            else:
                person = People(people_id=people_id)
                self.db.add(person)

            person.people_name = item.get("people_name")
            person.head_img = item.get("head_img")
            person.company = item.get("company")
            person.position = item.get("position")
            person.updated_at = datetime.utcnow()

            result["recent_joinees"].append(person)

        # 处理最近离职
        for item in data.get("recent_resignations", []):
            people_id = item.get("people_id")
            if not people_id:
                continue

            existing = self.db.query(People).filter(People.people_id == people_id).first()

            if existing:
                person = existing
            else:
                person = People(people_id=people_id)
                self.db.add(person)

            person.people_name = item.get("people_name")
            person.head_img = item.get("head_img")
            person.company = item.get("company")
            person.position = item.get("position")
            person.updated_at = datetime.utcnow()

            result["recent_resignations"].append(person)

        self.db.commit()
        return result

    async def batch_fetch_people(self, people_ids: List[int]) -> List[People]:
        """批量抓取人物"""
        people_list = []
        for pid in people_ids:
            try:
                person = await self.fetch_and_save_people(pid)
                people_list.append(person)
            except Exception as e:
                print(f"Failed to fetch people {pid}: {e}")
        return people_list

    def get_people(self, id: int) -> Optional[People]:
        """从数据库获取人物"""
        return self.db.query(People).filter(People.id == id).first()

    def get_people_by_people_id(self, people_id: int) -> Optional[People]:
        """通过RootData people_id获取人物"""
        return self.db.query(People).filter(People.people_id == people_id).first()

    def list_people(self, skip: int = 0, limit: int = 100) -> List[People]:
        """列出数据库中的人物"""
        return self.db.query(People).offset(skip).limit(limit).all()

    def get_people_as_dict(self, person: People) -> Dict:
        """将人物转换为字典"""
        return {
            "id": person.id,
            "people_id": person.people_id,
            "people_name": person.people_name,
            "head_img": person.head_img,
            "one_liner": person.one_liner,
            "introduce": person.introduce,
            "x": person.x,
            "linkedin": person.linkedin,
            "company": person.company,
            "position": person.position,
            "heat": person.heat,
            "influence": person.influence,
            "followers": person.followers,
            "created_at": person.created_at.isoformat() if person.created_at else None,
            "updated_at": person.updated_at.isoformat() if person.updated_at else None
        }
