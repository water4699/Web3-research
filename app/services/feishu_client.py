"""
飞书多维表格 API 客户端
"""
import httpx
import json
import gzip
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from app.config import get_settings

settings = get_settings()


def parse_feishu_base_file(file_path: str) -> Dict[str, Any]:
    """
    解析飞书多维表格的.base导出文件
    返回表格结构信息
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 解码并解压snapshot数据
        snapshot_data = base64.b64decode(data['gzipSnapshot'])
        snapshot_json = gzip.decompress(snapshot_data).decode('utf-8')
        snapshot = json.loads(snapshot_json)

        print(f"📄 快照数据类型: {type(snapshot)}")
        print(f"📄 快照数据结构: {list(snapshot.keys()) if isinstance(snapshot, dict) else '不是字典'}")

        # 提取表格信息
        table_info = {
            'name': '项目管理甘特图',  # 默认名称
            'fields': [],
            'views': []
        }

        # 尝试不同的数据结构
        try:
            # 情况1: snapshot是字典
            if isinstance(snapshot, dict):
                if 'name' in snapshot:
                    table_info['name'] = snapshot['name']

                # 查找字段信息
                if 'snapshot' in snapshot and isinstance(snapshot['snapshot'], dict):
                    meta = snapshot['snapshot'].get('meta', {})
                    if 'fieldMap' in meta:
                        for field_id, field_info in meta['fieldMap'].items():
                            table_info['fields'].append({
                                'id': field_id,
                                'name': field_info.get('name', ''),
                                'type': field_info.get('type', ''),
                                'property': field_info.get('property', {})
                            })

                    if 'viewMap' in meta:
                        for view_id, view_info in meta['viewMap'].items():
                            table_info['views'].append({
                                'id': view_id,
                                'name': view_info.get('name', ''),
                                'type': view_info.get('type', '')
                            })

            # 情况2: snapshot是列表或其他结构
            elif isinstance(snapshot, list) and len(snapshot) > 0:
                print(f"📄 快照是列表，长度: {len(snapshot)}")
                print(f"📄 第一个元素类型: {type(snapshot[0])}")

                # 尝试查找包含字段信息的对象
                for item in snapshot[:5]:  # 只检查前5个
                    if isinstance(item, dict) and 'meta' in item:
                        meta = item['meta']
                        if 'fieldMap' in meta:
                            print("✅ 找到字段信息！")
                            for field_id, field_info in meta['fieldMap'].items():
                                table_info['fields'].append({
                                    'id': field_id,
                                    'name': field_info.get('name', ''),
                                    'type': field_info.get('type', ''),
                                    'property': field_info.get('property', {})
                                })

                        if 'viewMap' in meta:
                            for view_id, view_info in meta['viewMap'].items():
                                table_info['views'].append({
                                    'id': view_id,
                                    'name': view_info.get('name', ''),
                                    'type': view_info.get('type', '')
                                })
                        break

        except Exception as parse_error:
            print(f"⚠️ 解析过程中出错: {parse_error}")

        # 如果没找到字段信息，提供默认的常见字段
        if not table_info['fields']:
            print("⚠️ 未找到字段信息，使用默认字段列表")
            table_info['fields'] = [
                {'id': '1', 'name': '项目名称', 'type': 1, 'property': {}},
                {'id': '2', 'name': '开始时间', 'type': 5, 'property': {}},
                {'id': '3', 'name': '结束时间', 'type': 5, 'property': {}},
                {'id': '4', 'name': '进度', 'type': 2, 'property': {}},
                {'id': '5', 'name': '负责人', 'type': 11, 'property': {}},
                {'id': '6', 'name': '项目状态', 'type': 3, 'property': {'options': [
                    {'name': '未开始'}, {'name': '进行中'}, {'name': '已完成'}, {'name': '暂停'}
                ]}},
                {'id': '7', 'name': '优先级', 'type': 3, 'property': {'options': [
                    {'name': '高'}, {'name': '中'}, {'name': '低'}
                ]}},
                {'id': '8', 'name': '里程碑', 'type': 1, 'property': {}},
                {'id': '9', 'name': '详细描述', 'type': 1, 'property': {}},
                {'id': '10', 'name': '投研报告', 'type': 6, 'property': {}},
                {'id': '11', 'name': '备注', 'type': 1, 'property': {}}
            ]

        return table_info

    except Exception as e:
        raise Exception(f"解析.base文件失败: {str(e)}")


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
    
    def __init__(self, base_file_path: str = None):
        self.client = FeishuClient()
        self.table_schema = None

        # 如果提供了.base文件路径，解析表格结构
        if base_file_path:
            try:
                self.table_schema = parse_feishu_base_file(base_file_path)
            except Exception as e:
                print(f"⚠️ 解析表格结构失败，使用默认映射: {e}")
                self.table_schema = None
    
    async def push_report(
        self,
        project_name: str,
        project_info: Dict,
        report_pdf_path: str = None,
        report_url: str = None,
        account_info: Dict = None,
        report_status: str = "已完成"
    ) -> str:
        """
        推送投研报告到飞书多维表格
        返回记录ID
        """
        # 构建字段数据（适配项目管理甘特图表格）
        fields = self._build_project_fields(
            project_name, project_info, report_pdf_path,
            report_url, account_info, report_status
        )

        result = await self.client.add_record(fields)
        return result.get("record", {}).get("record_id")

    def _build_project_fields(
        self,
        project_name: str,
        project_info: Dict,
        report_pdf_path: str = None,
        report_url: str = None,
        account_info: Dict = None,
        report_status: str = "已完成"
    ) -> Dict[str, Any]:
        """构建适配项目管理甘特图表格的字段数据"""

        # 映射项目状态
        status_mapping = {
            "已完成": "已完成",
            "生成中": "进行中",
            "失败": "暂停",
            "pending": "未开始",
            "generating": "进行中",
            "completed": "已完成",
            "failed": "暂停"
        }
        project_status = status_mapping.get(report_status, "未开始")

        # 基础项目信息 - 适配甘特图表格字段
        fields = {
            "项目名称": project_name,
            "项目状态": project_status,
            "优先级": "中",  # 默认中等优先级
        }

        # 日期字段：开始时间和结束时间
        if project_info.get("created_at"):
            try:
                if hasattr(project_info["created_at"], 'strftime'):
                    fields["开始时间"] = project_info["created_at"].strftime("%Y-%m-%d")
                else:
                    # 如果是字符串，尝试解析
                    created_date = datetime.fromisoformat(str(project_info["created_at"]).replace('Z', '+00:00'))
                    fields["开始时间"] = created_date.strftime("%Y-%m-%d")
            except:
                # 如果解析失败，使用今天作为开始时间
                fields["开始时间"] = datetime.now().strftime("%Y-%m-%d")

        # 估算结束时间（开始时间后3个月）
        if fields.get("开始时间"):
            try:
                start_date = datetime.strptime(fields["开始时间"], "%Y-%m-%d")
                # 计算3个月后的日期
                if start_date.month <= 9:
                    end_date = start_date.replace(month=start_date.month + 3)
                else:
                    end_date = start_date.replace(year=start_date.year + 1, month=start_date.month - 9)
                fields["结束时间"] = end_date.strftime("%Y-%m-%d")

                # 根据状态设置进度
                if project_status == "已完成":
                    fields["进度"] = 100
                elif project_status == "进行中":
                    fields["进度"] = 50
                else:
                    fields["进度"] = 0
            except:
                fields["进度"] = 0

        # 负责人信息（人员字段）
        if account_info and account_info.get('email'):
            fields["负责人"] = account_info['email']

        # 里程碑（文本字段，用换行分隔）
        milestones = []
        if report_status in ["已完成", "completed"]:
            milestones.append("✅ 项目数据抓取完成")
            milestones.append("✅ 投研报告生成完成")
            if report_pdf_path:
                milestones.append("✅ PDF报告上传完成")
            if report_url:
                milestones.append("✅ 报告链接生成完成")
        elif report_status in ["生成中", "generating"]:
            milestones.append("✅ 项目数据抓取完成")
            milestones.append("🔄 投研报告生成中...")
        else:
            milestones.append("❌ 报告生成失败")

        if milestones:
            fields["里程碑"] = "\n".join(milestones)

        # 详细描述（整合项目信息）
        description_parts = []
        description_parts.append(f"项目名称: {project_name}")

        if project_info.get("token_symbol"):
            description_parts.append(f"代币符号: {project_info['token_symbol']}")

        if project_info.get("one_liner"):
            description_parts.append(f"一句话介绍: {project_info['one_liner']}")

        if project_info.get("total_funding"):
            description_parts.append(f"融资总额: ${Number(project_info['total_funding']).toLocaleString()}")

        if project_info.get("tags"):
            description_parts.append(f"标签: {', '.join(project_info['tags'])}")

        if project_info.get("description"):
            description_parts.append(f"\n项目详细描述:\n{project_info['description'][:500]}{'...' if len(project_info['description']) > 500 else ''}")

        if project_info.get("investors"):
            investor_names = [inv.get("name", "") for inv in project_info["investors"][:5]]
            if investor_names:
                description_parts.append(f"\n主要投资者: {', '.join(investor_names)}")

        if project_info.get("social_media"):
            social_info = []
            if project_info["social_media"].get("website"):
                social_info.append(f"官网: {project_info['social_media']['website']}")
            if project_info["social_media"].get("twitter"):
                social_info.append(f"Twitter: {project_info['social_media']['twitter']}")
            if social_info:
                description_parts.append(f"\n社交媒体: {' | '.join(social_info)}")

        fields["详细描述"] = "\n".join(description_parts)

        # 附件：PDF报告（如果有）
        if report_pdf_path:
            try:
                import asyncio
                file_token = asyncio.run(self.client.upload_file(report_pdf_path))
                fields["投研报告"] = [{
                    "file_token": file_token
                }]
            except Exception as e:
                print(f"⚠️ PDF上传失败: {e}")

        # 备注信息（汇总其他重要信息）
        notes = []
        notes.append(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if project_info.get("active") is False:
            notes.append("⚠️ 项目已停止运营")

        if project_info.get("heat"):
            notes.append(f"热度值: {project_info['heat']}")

        if account_info:
            notes.append(f"报告生成账号: {account_info.get('email', '未知')}")
            if 'weekly_quota_used' in account_info and 'weekly_quota_limit' in account_info:
                notes.append(f"账号额度: {account_info['weekly_quota_used']}/{account_info['weekly_quota_limit']}")
        
        if report_url:
            notes.append(f"报告链接: {report_url}")

        fields["备注"] = "\n".join(notes)

        return fields

    def get_table_schema(self) -> Dict[str, Any]:
        """获取解析的表格结构信息"""
        return self.table_schema

    def print_table_info(self):
        """打印表格结构信息"""
        if not self.table_schema:
            print("未提供.base文件，无法解析表格结构")
            return

        print("📊 表格信息:")
        print(f"表格名称: {self.table_schema.get('name', '未知')}")

        print(f"\n📋 字段列表 ({len(self.table_schema.get('fields', []))} 个字段):")
        for field in self.table_schema.get('fields', []):
            print(f"  • {field['name']} (类型: {field['type']})")

        print(f"\n👁️ 视图列表 ({len(self.table_schema.get('views', []))} 个视图):")
        for view in self.table_schema.get('views', []):
            print(f"  • {view['name']} (类型: {view['type']})")
    
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
