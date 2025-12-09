"""
RootData API 客户端
支持两种抓取模式：
1. basic - 基本信息（不含Pro字段）
2. full - 全部信息（含Pro字段）
"""
import httpx
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from app.config import get_settings

settings = get_settings()


class FetchMode(str, Enum):
    BASIC = "basic"
    FULL = "full"


class RootDataClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.rootdata_api_key
        self.base_url = settings.rootdata_base_url
        self.headers = {
            "apikey": self.api_key,
            "language": "cn",
            "Content-Type": "application/json"
        }
    
    async def _request(self, endpoint: str, data: dict = None) -> Dict[str, Any]:
        """发送POST请求"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{endpoint}",
                headers=self.headers,
                json=data or {},
                timeout=30
            )
            result = response.json()
            if result.get("result") != 200:
                raise Exception(f"RootData API Error: {result.get('message', 'Unknown error')}")
            return result
    
    # ==================== 免费/基础接口 ====================
    
    async def search(self, query: str, precise_x_search: bool = False) -> List[Dict]:
        """
        搜索项目/机构/人物 (不限次数)
        返回: [{id, type, name, logo, introduce, active, rootdataurl}]
        type: 1=项目, 2=机构, 3=人物
        """
        result = await self._request("ser_inv", {
            "query": query,
            "precise_x_search": precise_x_search
        })
        return result.get("data", [])
    
    async def get_quota(self) -> Dict:
        """
        查询API余额 (免费)
        返回: {apikey, start, end, level, total_credits, credits, last_mo_credits}
        """
        result = await self._request("quotacredits")
        return result.get("data", {})
    
    # ==================== 项目信息接口 ====================
    
    async def get_project(
        self, 
        project_id: int = None,
        contract_address: str = None,
        mode: FetchMode = FetchMode.BASIC
    ) -> Dict:
        """
        获取项目详情 (2 credits/次)
        
        Args:
            project_id: 项目ID
            contract_address: 合约地址
            mode: 
                - BASIC: 基本信息（不含Pro字段）
                - FULL: 全部信息（含Pro字段，如ecosystem, market_cap, price等）
        """
        data = {}
        if project_id:
            data["project_id"] = project_id
        elif contract_address:
            data["contract_address"] = contract_address
        else:
            raise ValueError("必须提供 project_id 或 contract_address")
        
        # 是否包含团队和投资者信息
        if mode == FetchMode.FULL:
            data["include_team"] = True
            data["include_investors"] = True
        
        result = await self._request("get_item", data)
        project_data = result.get("data", {})
        
        # 标记抓取模式
        project_data["_fetch_mode"] = mode.value
        
        return project_data
    
    async def get_project_basic(self, project_id: int) -> Dict:
        """获取项目基本信息"""
        return await self.get_project(project_id=project_id, mode=FetchMode.BASIC)
    
    async def get_project_full(self, project_id: int) -> Dict:
        """获取项目全部信息（含Pro字段）"""
        return await self.get_project(project_id=project_id, mode=FetchMode.FULL)
    
    # ==================== 批量接口 ====================
    
    async def get_id_list(self, type_: int) -> List[Dict]:
        """
        获取ID列表 (20 Credits/次, Plus/Pro)
        type_: 1=项目, 2=机构, 3=人物
        返回: [{id, name}]
        """
        result = await self._request("id_map", {"type": type_})
        return result.get("data", [])
    
    async def get_hot_projects(self, days: int = 7) -> List[Dict]:
        """
        获取热门项目Top100 (10 credits/次, Pro)
        days: 1 或 7
        """
        result = await self._request("hot_index", {"days": days})
        return result.get("data", [])
    
    async def get_funding_rounds(
        self,
        page: int = 1,
        page_size: int = 10,
        start_time: str = None,
        end_time: str = None,
        min_amount: int = None,
        max_amount: int = None,
        project_id: int = None
    ) -> Dict:
        """
        批量获取投资轮次 (2 credits/条, Plus/Pro)
        """
        data = {"page": page, "page_size": page_size}
        if start_time:
            data["start_time"] = start_time
        if end_time:
            data["end_time"] = end_time
        if min_amount:
            data["min_amount"] = min_amount
        if max_amount:
            data["max_amount"] = max_amount
        if project_id:
            data["project_id"] = project_id
        
        result = await self._request("get_fac", data)
        return result.get("data", {})
    
    # ==================== Pro专属接口 ====================
    
    async def get_ecosystem_map(self) -> List[Dict]:
        """获取生态版图 (50 credits/次, Pro)"""
        result = await self._request("ecosystem_map")
        return result.get("data", [])
    
    async def get_projects_by_ecosystem(self, ecosystem_ids: str) -> List[Dict]:
        """根据生态获取项目 (20 credits/次, Pro)"""
        result = await self._request("projects_by_ecosystems", {"ecosystem_ids": ecosystem_ids})
        return result.get("data", [])
    
    async def get_projects_by_tags(self, tag_ids: str) -> List[Dict]:
        """根据标签获取项目 (20 credits/次, Pro)"""
        result = await self._request("projects_by_tags", {"tag_ids": tag_ids})
        return result.get("data", [])
    
    async def get_new_tokens(self) -> List[Dict]:
        """获取近期发币项目 (10 credits/次, Pro)"""
        result = await self._request("new_tokens")
        return result.get("data", [])

    # ==================== VC/机构接口 ====================
    
    async def get_vc(
        self,
        org_id: int,
        include_team: bool = False,
        include_investments: bool = False
    ) -> Dict:
        """
        获取VC/机构详情 (2 credits/次)
        
        Args:
            org_id: 机构ID
            include_team: 是否包含团队成员信息
            include_investments: 是否包含投资项目信息
        """
        data = {
            "org_id": org_id,
            "include_team": include_team,
            "include_investments": include_investments
        }
        result = await self._request("get_org", data)
        return result.get("data", {})

    async def get_investor_batches(
        self,
        page: int = 1,
        page_size: int = 10
    ) -> Dict:
        """
        批量获取投资者详细信息 (2 credits/条, Plus/Pro)
        """
        result = await self._request("get_invest", {
            "page": page,
            "page_size": page_size
        })
        return result.get("data", {})

    # ==================== 人物接口 ====================
    
    async def get_people(self, people_id: int) -> Dict:
        """
        获取人物详情 (2 credits/次, Pro)
        """
        result = await self._request("get_people", {"people_id": people_id})
        return result.get("data", {})

    async def get_hot_people_on_x(
        self,
        heat: bool = False,
        influence: bool = False,
        followers: bool = False
    ) -> Dict:
        """
        获取X热门人物 (10 credits/次, Pro)
        """
        result = await self._request("hot_people_on_x", {
            "heat": heat,
            "influence": influence,
            "followers": followers
        })
        return result.get("data", {})

    async def get_job_changes(
        self,
        recent_joinees: bool = True,
        recent_resignations: bool = True
    ) -> Dict:
        """
        获取人物职位变动 (10 credits/次, Pro)
        """
        result = await self._request("job_changes", {
            "recent_joinees": recent_joinees,
            "recent_resignations": recent_resignations
        })
        return result.get("data", {})

    # ==================== X数据接口 ====================
    
    async def get_x_data_batches(self, type_: int) -> List[Dict]:
        """
        批量获取X数据 (50 credits/次, Plus/Pro)
        type_: 1=项目, 2=机构, 3=人物
        返回: [{id, name, X, followers, following, heat, influence}]
        """
        result = await self._request("twitter_map", {"type": type_})
        return result.get("data", [])

    async def get_hot_projects_on_x(
        self,
        heat: bool = False,
        influence: bool = False,
        followers: bool = False
    ) -> Dict:
        """
        获取X热门项目 (10 credits/次, Pro)
        """
        result = await self._request("hot_project_on_x", {
            "heat": heat,
            "influence": influence,
            "followers": followers
        })
        return result.get("data", {})

    # ==================== 同步更新接口 ====================
    
    async def get_sync_updates(
        self,
        begin_time: int,
        end_time: int = None
    ) -> List[Dict]:
        """
        获取数据更新列表 (1 credit/条, Pro)
        
        Args:
            begin_time: 开始时间戳
            end_time: 结束时间戳
        返回: [{id, type, name, update_time}]
        """
        data = {"begin_time": begin_time}
        if end_time:
            data["end_time"] = end_time
        result = await self._request("ser_change", data)
        return result.get("data", [])

    # ==================== 标签接口 ====================
    
    async def get_tag_map(self) -> List[Dict]:
        """
        获取标签列表 (50 credits/次, Pro)
        返回: [{tag_id, tag_name}]
        """
        result = await self._request("tag_map")
        return result.get("data", [])


# 便捷函数
async def fetch_project(project_id: int, mode: str = "basic") -> Dict:
    """
    抓取项目信息的便捷函数
    
    Args:
        project_id: RootData 项目ID
        mode: "basic" 或 "full"
    """
    client = RootDataClient()
    fetch_mode = FetchMode.FULL if mode == "full" else FetchMode.BASIC
    return await client.get_project(project_id=project_id, mode=fetch_mode)
