"""
飞书多维表格 API 客户端
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from app.config import get_settings

settings = get_settings()


class FeishuClient:
    def __init__(self):
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        self.base_url = settings.feishu_base_url
        self.bitable_app_token = settings.feishu_bitable_app_token
        self.table_id = settings.feishu_bitable_table_id
        self._access_token = None
        self._token_expires_at = None
    
    async def _get_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._access_token and self._token_expires_at:
            if datetime.now().timestamp() < self._token_expires_at:
                return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                }
            )
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Failed to get access token: {data.get('msg')}")
            
            self._access_token = data["tenant_access_token"]
            self._token_expires_at = datetime.now().timestamp() + data.get("expire", 7200) - 300
            
            return self._access_token
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: dict = None,
        files: dict = None
    ) -> Dict[str, Any]:
        """发送请求"""
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    params=data
                )
            elif method == "POST":
                if files:
                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        data=data,
                        files=files
                    )
                else:
                    headers["Content-Type"] = "application/json"
                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        json=data
                    )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"Feishu API Error: {result.get('msg')}")
            
            return result
    
    # ==================== 多维表格操作 ====================
    
    async def add_record(
        self,
        fields: Dict[str, Any],
        app_token: str = None,
        table_id: str = None
    ) -> Dict:
        """
        新增单条记录到多维表格
        
        Args:
            fields: 字段数据，如 {"项目名称": "Bitcoin", "融资金额": 1000000}
            app_token: 多维表格app_token（可选，默认使用配置）
            table_id: 数据表ID（可选，默认使用配置）
        """
        app_token = app_token or self.bitable_app_token
        table_id = table_id or self.table_id
        
        result = await self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            {"fields": fields}
        )
        return result.get("data", {})
    
    async def batch_add_records(
        self,
        records: List[Dict[str, Any]],
        app_token: str = None,
        table_id: str = None
    ) -> Dict:
        """
        批量新增记录
        
        Args:
            records: 记录列表，每条记录格式为 {"fields": {"字段名": "值"}}
        """
        app_token = app_token or self.bitable_app_token
        table_id = table_id or self.table_id
        
        result = await self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            {"records": records}
        )
        return result.get("data", {})
    
    async def update_record(
        self,
        record_id: str,
        fields: Dict[str, Any],
        app_token: str = None,
        table_id: str = None
    ) -> Dict:
        """更新记录"""
        app_token = app_token or self.bitable_app_token
        table_id = table_id or self.table_id
        
        result = await self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            {"fields": fields}
        )
        return result.get("data", {})
    
    async def get_records(
        self,
        page_size: int = 100,
        page_token: str = None,
        app_token: str = None,
        table_id: str = None
    ) -> Dict:
        """获取记录列表"""
        app_token = app_token or self.bitable_app_token
        table_id = table_id or self.table_id
        
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        
        result = await self._request(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params
        )
        return result.get("data", {})
    
    # ==================== 文件上传 ====================
    
    async def upload_file(
        self,
        file_path: str,
        parent_type: str = "bitable_file",
        parent_node: str = None
    ) -> str:
        """
        上传文件到飞书
        返回file_token
        """
        app_token = parent_node or self.bitable_app_token
        path = Path(file_path)
        
        async with httpx.AsyncClient() as client:
            token = await self._get_access_token()
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (path.name, f, 'application/pdf')
                }
                data = {
                    'file_name': path.name,
                    'parent_type': parent_type,
                    'parent_node': app_token,
                    'size': str(path.stat().st_size)
                }
                
                response = await client.post(
                    f"{self.base_url}/drive/v1/medias/upload_all",
                    headers={"Authorization": f"Bearer {token}"},
                    data=data,
                    files=files
                )
                
                result = response.json()
                if result.get("code") != 0:
                    raise Exception(f"Upload failed: {result.get('msg')}")
                
                return result["data"]["file_token"]


class ReportPusher:
    """投研报告推送到飞书"""
    
    def __init__(self):
        self.client = FeishuClient()
    
    async def push_report(
        self,
        project_name: str,
        project_info: Dict,
        report_pdf_path: str = None,
        report_url: str = None
    ) -> str:
        """
        推送投研报告到飞书多维表格
        返回记录ID
        """
        # 构建字段数据（根据你的表格结构调整）
        fields = {
            "项目名称": project_name,
            "代币符号": project_info.get("token_symbol", ""),
            "一句话介绍": project_info.get("one_liner", ""),
            "融资总额": project_info.get("total_funding", 0),
            "标签": ", ".join(project_info.get("tags", [])),
            "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 如果有PDF，先上传
        if report_pdf_path:
            file_token = await self.client.upload_file(report_pdf_path)
            fields["投研报告"] = [{
                "file_token": file_token
            }]
        
        if report_url:
            fields["报告链接"] = report_url
        
        result = await self.client.add_record(fields)
        return result.get("record", {}).get("record_id")
    
    async def batch_push_projects(self, projects: List[Dict]) -> List[str]:
        """批量推送项目信息"""
        records = []
        for project in projects:
            records.append({
                "fields": {
                    "项目名称": project.get("name", ""),
                    "代币符号": project.get("token_symbol", ""),
                    "一句话介绍": project.get("one_liner", ""),
                    "融资总额": project.get("total_funding", 0),
                    "标签": ", ".join(project.get("tags", [])),
                }
            })
        
        result = await self.client.batch_add_records(records)
        return [r.get("record_id") for r in result.get("records", [])]
