// API Base URL
const API_BASE = '';

// 图片代理函数
function getImageUrl(originalUrl) {
    if (!originalUrl) return '';

    // 如果是RootData图片，使用代理
    if (originalUrl.includes('public.rootdata.com')) {
        // 提取图片路径部分
        const pathMatch = originalUrl.match(/\/images\/(.+)$/);
        if (pathMatch) {
            return `${API_BASE}/api/image/${pathMatch[1]}`;
        }
    }

    return originalUrl;
}

// 图片加载错误处理
function handleImageError(img) {
    img.style.display = 'none';
    // 创建一个占位符div
    const placeholder = document.createElement('div');
    placeholder.style.cssText = `
        width: 24px;
        height: 24px;
        border-radius: 4px;
        background: var(--bg-hover);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        color: var(--text-muted);
    `;
    placeholder.textContent = '图';

    // 替换图片元素
    if (img.parentNode) {
        img.parentNode.replaceChild(placeholder, img);
    }
}

// 页面切换
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        
        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        
        // 切换页面
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');
        
        // 加载页面数据
        if (page === 'dashboard') loadDashboard();
        if (page === 'projects') loadProjects();
        if (page === 'fetch') initSearchInput();
        if (page === 'reports') { loadReports(); loadProjectsForSelect(); }
        if (page === 'accounts') loadAccounts();
        if (page === 'test') loadTestResults(1);
    });
});

// Toast 通知
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// API 请求封装
async function api(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || '请求失败');
        return data;
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

// ==================== 仪表盘 ====================
async function loadDashboard() {
    try {
        const [projects, reports, accounts] = await Promise.all([
            api('/api/projects?limit=5'),
            api('/api/reports?limit=5'),
            api('/api/surf/accounts')
        ]);
        
        // 顶部统计
        document.getElementById('stat-projects').textContent = projects.count || 0;
        document.getElementById('stat-reports').textContent = reports.data?.length || 0;
        document.getElementById('stat-accounts').textContent = accounts.data?.length || 0;
        document.getElementById('stat-quota').textContent = accounts.total_remaining_quota || 0;

        renderDashboardProjects(projects.data || []);
        renderDashboardReports(reports.data || []);
        renderDashboardAccounts(accounts);
    } catch (e) {
        console.error('Failed to load dashboard:', e);
    }
}

function renderDashboardProjects(list) {
    const container = document.getElementById('dashboard-projects');
    if (!list.length) {
        container.classList.add('empty-tip');
        container.innerHTML = '暂无项目，请先抓取数据';
        return;
    }
    container.classList.remove('empty-tip');
    container.innerHTML = list.map(p => `
        <div class="dashboard-item">
            <div class="dashboard-item-title">
                <div class="item-main">
                    <strong>${p.name || '-'}</strong>
                    <span class="sub-text">${p.token_symbol || '无代币'} · 抓取模式：${p.fetch_mode || 'basic'}</span>
                </div>
                <span class="badge">${p.fetch_mode || '-'}</span>
            </div>
            <div class="dashboard-meta">
                <span><i class="ri-calendar-line"></i> ${p.created_at ? new Date(p.created_at).toLocaleString() : '-'}</span>
                <span><i class="ri-coins-line"></i> ${p.total_funding ? '$' + Number(p.total_funding).toLocaleString() : '融资未知'}</span>
            </div>
        </div>
    `).join('');
}

function renderDashboardReports(list) {
    const container = document.getElementById('dashboard-reports');
    if (!list.length) {
        container.classList.add('empty-tip');
        container.innerHTML = '暂无报告，去生成一份吧';
        return;
    }
    container.classList.remove('empty-tip');
    container.innerHTML = list.map(r => `
        <div class="dashboard-item">
            <div class="dashboard-item-title">
                <div class="item-main">
                    <strong>报告 #${r.id}</strong>
                    <span class="sub-text">项目ID：${r.project_id}</span>
                </div>
                <span class="status status-${r.status}">${r.status}</span>
            </div>
            <div class="dashboard-meta">
                <span><i class="ri-time-line"></i> ${r.created_at ? new Date(r.created_at).toLocaleString() : '-'}</span>
                <span><i class="ri-share-box-line"></i> ${r.feishu_record_id ? '已推送飞书' : '未推送'}</span>
            </div>
        </div>
    `).join('');
}

function renderDashboardAccounts(accountsData) {
    const container = document.getElementById('dashboard-accounts');
    const list = accountsData.data || [];
    if (!list.length) {
        container.classList.add('empty-tip');
        container.innerHTML = '暂无 Surf 账号，请先添加';
        return;
    }
    container.classList.remove('empty-tip');
    container.innerHTML = list.map(acc => `
        <div class="dashboard-item">
            <div class="dashboard-item-title">
                <div class="item-main">
                    <strong>${acc.email}</strong>
                    <span class="sub-text">已用 ${acc.weekly_quota_used}/${acc.weekly_quota_limit}</span>
                </div>
                <span class="status status-${acc.status}">${acc.status}</span>
            </div>
            <div class="dashboard-meta">
                <span><i class="ri-battery-line"></i> 剩余额度：${acc.remaining}</span>
                <span><i class="ri-time-line"></i> ${acc.last_used_at ? new Date(acc.last_used_at).toLocaleString() : '未使用'}</span>
            </div>
        </div>
    `).join('');
}

async function loadQuota() {
    try {
        const data = await api('/api/quota');
        document.getElementById('quota-info').innerHTML = `
            <p><strong>API等级:</strong> ${data.level || 'N/A'}</p>
            <p><strong>剩余Credits:</strong> ${data.credits || 0} / ${data.total_credits || 0}</p>
            <p><strong>有效期至:</strong> ${data.end ? new Date(data.end).toLocaleDateString() : 'N/A'}</p>
        `;
        showToast('配额信息已刷新');
    } catch (e) {
        document.getElementById('quota-info').innerHTML = '<p style="color: var(--danger)">获取失败，请检查API Key配置</p>';
    }
}

// ==================== 项目管理 ====================
async function loadProjects() {
    try {
        const tbody = document.getElementById('projects-table');
        // loading 状态
        tbody.innerHTML = '<tr><td colspan="6" class="empty">加载中...</td></tr>';
        // 隐藏详情
        const detailDiv = document.getElementById('project-detail');
        if (detailDiv) detailDiv.style.display = 'none';

        const data = await api('/api/projects?limit=100');
        
        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">暂无数据</td></tr>';
            showToast('暂无项目数据', 'info');
            return;
        }
        
        tbody.innerHTML = data.data.map(p => `
            <tr>
                <td>${p.id}</td>
                <td>
                    <div style="display:flex;align-items:center;gap:8px;">
                        ${p.logo ? `<img src="${getImageUrl(p.logo)}" style="width:24px;height:24px;border-radius:4px;" onerror="handleImageError(this)">` : ''}
                        ${p.name || '-'}
                    </div>
                </td>
                <td>${p.token_symbol || '-'}</td>
                <td>${p.total_funding ? '$' + Number(p.total_funding).toLocaleString() : '-'}</td>
                <td><span class="status status-${p.fetch_mode === 'full' ? 'active' : 'pending'}">${p.fetch_mode || '-'}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewProject(${p.id})">查看</button>
                </td>
            </tr>
        `).join('');
        showToast('列表已刷新');
    } catch (e) {
        console.error('Failed to load projects:', e);
        const tbody = document.getElementById('projects-table');
        tbody.innerHTML = '<tr><td colspan="6" class="empty" style="color: var(--danger);">加载失败，请重试</td></tr>';
        showToast('刷新失败，请检查网络或服务器', 'error');
    }
}

async function viewProject(id) {
    try {
        const detailDiv = document.getElementById('project-detail');
        const detailContent = document.getElementById('project-detail-content');
        const detailTitle = document.getElementById('detail-title');

        // 显示详情区域
        detailDiv.style.display = 'block';
        detailContent.innerHTML = '<div class="loading">加载中...</div>';

        // 滚动到详情区域
        detailDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

        const data = await api(`/api/projects/${id}`);

        // 渲染项目详情
        const project = data;
        detailTitle.textContent = `${project.name} - 项目详情`;

        detailContent.innerHTML = `
            <div class="project-detail-grid">
                <div class="detail-section">
                    <h4>基本信息</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>项目ID:</label>
                            <span>${project.id}</span>
                        </div>
                        <div class="detail-item">
                            <label>项目名称:</label>
                            <span>${project.name || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>代币符号:</label>
                            <span>${project.token_symbol || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>成立时间:</label>
                            <span>${project.establishment_date || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>融资总额:</label>
                            <span>${project.total_funding ? '$' + Number(project.total_funding).toLocaleString() : '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>活跃状态:</label>
                            <span class="status ${project.active ? 'status-active' : 'status-inactive'}">${project.active ? '活跃' : '不活跃'}</span>
                        </div>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>项目简介</h4>
                    <p class="project-description">${project.one_liner || '暂无简介'}</p>
                </div>

                ${project.description ? `
                <div class="detail-section">
                    <h4>详细描述</h4>
                    <div class="project-description">${project.description}</div>
                </div>
                ` : ''}

                ${project.tags && project.tags.length > 0 ? `
                <div class="detail-section">
                    <h4>标签</h4>
                    <div class="tags-list">
                        ${project.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                    </div>
                </div>
                ` : ''}

                ${project.investors && project.investors.length > 0 ? `
                <div class="detail-section">
                    <h4>投资者</h4>
                    <div class="investors-list">
                        ${project.investors.slice(0, 10).map(investor =>
                            investor.logo ?
                            `<div class="investor-item"><img src="${getImageUrl(investor.logo)}" alt="${investor.name}" onerror="handleImageError(this)"> <span>${investor.name}</span></div>` :
                            `<div class="investor-item"><span>${investor.name}</span></div>`
                        ).join('')}
                        ${project.investors.length > 10 ? `<div class="investor-item"><span>... 还有 ${project.investors.length - 10} 个投资者</span></div>` : ''}
                    </div>
                </div>
                ` : ''}

                ${project.social_media ? `
                <div class="detail-section">
                    <h4>社交媒体</h4>
                    <div class="social-links">
                        ${project.social_media.website ? `<a href="${project.social_media.website}" target="_blank" class="social-link"><i class="ri-global-line"></i> 官网</a>` : ''}
                        ${project.social_media.twitter ? `<a href="${project.social_media.twitter}" target="_blank" class="social-link"><i class="ri-twitter-line"></i> Twitter</a>` : ''}
                        ${project.social_media.telegram ? `<a href="${project.social_media.telegram}" target="_blank" class="social-link"><i class="ri-telegram-line"></i> Telegram</a>` : ''}
                        ${project.social_media.discord ? `<a href="${project.social_media.discord}" target="_blank" class="social-link"><i class="ri-discord-line"></i> Discord</a>` : ''}
                        ${project.social_media.github ? `<a href="${project.social_media.github}" target="_blank" class="social-link"><i class="ri-github-line"></i> GitHub</a>` : ''}
                    </div>
                </div>
                ` : ''}

                <div class="detail-section">
                    <h4>数据信息</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>抓取模式:</label>
                            <span class="status status-${project.fetch_mode === 'full' ? 'active' : 'pending'}">${project.fetch_mode || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>创建时间:</label>
                            <span>${project.created_at ? new Date(project.created_at).toLocaleString() : '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>更新时间:</label>
                            <span>${project.updated_at ? new Date(project.updated_at).toLocaleString() : '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>RootData ID:</label>
                            <span>${project.rootdata_id || '-'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

    } catch (e) {
        console.error('Failed to load project detail:', e);
        showToast('加载项目详情失败', 'error');
    }
}

function hideProjectDetail() {
    const detailDiv = document.getElementById('project-detail');
    detailDiv.style.display = 'none';
}

// ==================== 数据抓取 ====================
// 实时搜索相关变量
let searchTimeout = null;
let currentSearchQuery = '';

async function searchProjects(query = null) {
    const searchQuery = query || document.getElementById('search-query').value.trim();

    if (!searchQuery) {
        const container = document.getElementById('search-results');
        container.innerHTML = '<p class="hint">请输入项目名称或代币符号进行搜索</p>';
        return;
    }

    if (searchQuery === currentSearchQuery) return;

    currentSearchQuery = searchQuery;
    
    try {
        const data = await api('/api/projects/search', {
            method: 'POST',
            body: JSON.stringify({ query: searchQuery })
        });
        
        const container = document.getElementById('search-results');
        if (!data.data || data.data.length === 0) {
            container.innerHTML = `<p class="hint">未找到包含"${searchQuery}"的项目</p>`;
            return;
        }
        
        container.innerHTML = data.data.slice(0, 20).map(p => `
            <div class="search-item" onclick="selectProject(${p.id}, '${p.name.replace(/'/g, "\\'")}')">
                ${p.logo ? `<img src="${getImageUrl(p.logo)}" alt="" onerror="handleImageError(this)">` : '<div style="width:40px;height:40px;background:var(--bg-hover);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;color:var(--text-muted);">图</div>'}
                <div class="search-item-info">
                    <div class="search-item-name">${p.name} ${p.active === false ? '(已停止)' : ''}</div>
                    <div class="search-item-desc">${p.introduce || '暂无介绍'}</div>
                </div>
                <span style="color:var(--text-muted);font-size:12px;">ID: ${p.id}</span>
            </div>
        `).join('');
        
        // 只在非实时搜索时显示Toast
        if (query) {
        showToast(`找到 ${data.count} 个项目`);
        }

    } catch (e) {
        console.error('Search failed:', e);
        const container = document.getElementById('search-results');
        container.innerHTML = '<p class="hint" style="color: var(--danger);">搜索失败，请稍后重试</p>';
    }
}

// 实时搜索处理函数
function handleSearchInput() {
    const query = document.getElementById('search-query').value.trim();

    // 清除之前的定时器
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    // 如果查询为空，显示提示
    if (!query) {
        const container = document.getElementById('search-results');
        container.innerHTML = '<p class="hint">请输入项目名称或代币符号进行搜索</p>';
        return;
    }

    // 设置新的定时器，延迟500ms执行搜索
    searchTimeout = setTimeout(() => {
        searchProjects();
    }, 500);
}

// 初始化搜索输入框事件监听
function initSearchInput() {
    const searchInput = document.getElementById('search-query');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearchInput);
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                // 立即执行搜索
                if (searchTimeout) {
                    clearTimeout(searchTimeout);
                }
                searchProjects();
            }
        });
    }
}

function selectProject(id, name) {
    document.getElementById('fetch-project-id').value = id;
    showToast(`已选择: ${name} (ID: ${id})`);
}

async function fetchProject() {
    const projectId = document.getElementById('fetch-project-id').value;
    const mode = document.getElementById('fetch-mode').value;
    
    if (!projectId) {
        showToast('请输入项目ID', 'error');
        return;
    }
    
    try {
        const data = await api('/api/projects/fetch', {
            method: 'POST',
            body: JSON.stringify({ project_id: parseInt(projectId), mode })
        });
        showToast(data.message || '抓取成功');
    } catch (e) {}
}

async function fetchHotProjects() {
    const days = document.getElementById('hot-days').value;
    const mode = document.getElementById('hot-mode').value;
    
    if (!confirm(`确定要抓取近${days}天的热门项目Top100吗？\n此操作将消耗 10 credits 并批量抓取项目。`)) {
        return;
    }
    
    try {
        const data = await api(`/api/projects/hot?days=${days}&mode=${mode}`);
        showToast(data.message || '热门项目抓取完成');
    } catch (e) {}
}

// ==================== 投研报告 ====================
async function loadReports() {
    try {
        const data = await api('/api/reports');
        const tbody = document.getElementById('reports-table');
        
        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">暂无数据</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.data.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${r.project_id}</td>
                <td><span class="status status-${r.status}">${r.status}</span></td>
                <td>${r.pdf_path || '-'}</td>
                <td>${r.feishu_record_id || '-'}</td>
                <td>${r.created_at ? new Date(r.created_at).toLocaleString() : '-'}</td>
            </tr>
        `).join('');
    } catch (e) {}
}

async function loadProjectsForSelect() {
    try {
        const data = await api('/api/projects?limit=1000');
        const select = document.getElementById('report-project-id');
        
        if (!data.data || data.data.length === 0) {
            select.innerHTML = '<option value="">-- 暂无项目，请先抓取 --</option>';
            return;
        }
        
        select.innerHTML = '<option value="">-- 选择项目 --</option>' + 
            data.data.map(p => `<option value="${p.id}">${p.name} (${p.token_symbol || 'N/A'})</option>`).join('');
    } catch (e) {}
}

async function generateReport() {
    const projectId = document.getElementById('report-project-id').value;
    const mode = document.getElementById('report-mode').value;
    
    if (!projectId) {
        showToast('请选择项目', 'error');
        return;
    }
    
    const modeDesc = mode === 'research' ? '深度研究（约3-10分钟）' : '快速问答（约30秒-1分钟）';
    if (!confirm(`确定要生成投研报告吗？\n\n模式：${modeDesc}\n\n${mode === 'research' ? '注意：深度研究每周仅2次免费额度' : ''}`)) {
        return;
    }
    
    try {
        const data = await api('/api/reports/generate', {
            method: 'POST',
            body: JSON.stringify({ project_id: parseInt(projectId), mode: mode })
        });
        showToast(data.message || '报告生成任务已启动');
        setTimeout(loadReports, 2000);
    } catch (e) {}
}

// ==================== Surf账号 ====================
async function loadAccounts() {
    try {
        const data = await api('/api/surf/accounts');
        const tbody = document.getElementById('accounts-table');
        
        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty">暂无账号</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.data.map(a => `
            <tr>
                <td>${a.id}</td>
                <td>${a.email}</td>
                <td><span class="status status-${a.status}">${a.status}</span></td>
                <td>${a.weekly_quota_used} / ${a.weekly_quota_limit}</td>
                <td>${a.remaining}</td>
                <td>${a.last_used_at ? new Date(a.last_used_at).toLocaleString() : '-'}</td>
                <td>
                    ${a.status === 'disabled' 
                        ? `<button class="btn btn-sm btn-success" onclick="enableAccount(${a.id})">启用</button>`
                        : `<button class="btn btn-sm btn-danger" onclick="disableAccount(${a.id})">禁用</button>`
                    }
                </td>
            </tr>
        `).join('');
    } catch (e) {}
}

async function addAccount() {
    const email = document.getElementById('account-email').value.trim();
    const password = document.getElementById('account-password').value;
    
    if (!email || !password) {
        showToast('请填写邮箱和密码', 'error');
        return;
    }
    
    try {
        const data = await api('/api/surf/accounts', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        showToast(data.message || '账号添加成功');
        document.getElementById('account-email').value = '';
        document.getElementById('account-password').value = '';
        loadAccounts();
    } catch (e) {}
}

async function disableAccount(id) {
    if (!confirm('确定要禁用此账号吗？')) return;
    
    try {
        await api(`/api/surf/accounts/${id}`, { method: 'DELETE' });
        showToast('账号已禁用');
        loadAccounts();
    } catch (e) {}
}

async function enableAccount(id) {
    if (!confirm('确定要启用此账号吗？')) return;
    
    try {
        await api(`/api/surf/accounts/${id}/enable`, { method: 'PUT' });
        showToast('账号已启用');
        loadAccounts();
    } catch (e) {}
}

// ==================== 飞书推送 ====================
async function pushToFeishu() {
    const reportId = document.getElementById('push-report-id').value;
    
    if (!reportId) {
        showToast('请输入报告ID', 'error');
        return;
    }
    
    try {
        const data = await api(`/api/feishu/push/${reportId}`, { method: 'POST' });
        showToast(data.message || '推送成功');
    } catch (e) {}
}

// ==================== 测试功能 ====================
// 分页相关变量
let currentTestPage = 1;
let currentTestFilterQuery = '';
let currentTestFilterType = '';

async function testSearchAndSave() {
    const query = document.getElementById('test-search-query').value.trim();
    const preciseSearch = document.getElementById('test-precise-search').value === 'true';
    
    if (!query) {
        showToast('请输入搜索关键词', 'error');
        return;
    }
    
    try {
        const data = await api(`/api/test/search-and-save?query=${encodeURIComponent(query)}&precise_x_search=${preciseSearch}`, {
            method: 'POST'
        });
        showToast(data.message || '搜索并保存成功');
        loadTestResults(1);
    } catch (e) {}
}

async function loadTestResults(page = 1) {
    try {
        const filterQuery = document.getElementById('test-filter-query')?.value.trim() || '';
        const filterType = document.getElementById('test-filter-type')?.value || '';
        
        // 保存当前筛选条件
        currentTestFilterQuery = filterQuery;
        currentTestFilterType = filterType;
        currentTestPage = page;

        let url = `/api/test/search-results?page=${page}&page_size=10`;
        if (filterQuery) url += `&query=${encodeURIComponent(filterQuery)}`;
        if (filterType) url += `&entity_type=${filterType}`;
        
        const data = await api(url);
        const tbody = document.getElementById('test-results-table');
        const paginationDiv = document.getElementById('test-pagination');
        
        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">暂无数据</td></tr>';
            paginationDiv.style.display = 'none';
            return;
        }
        
        tbody.innerHTML = data.data.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${r.query}</td>
                <td><span class="status status-${r.entity_type === 1 ? 'active' : r.entity_type === 2 ? 'pending' : 'inactive'}">${r.type_name}</span></td>
                <td>
                    <div style="display:flex;align-items:center;gap:8px;">
                        ${r.logo ? `<img src="${getImageUrl(r.logo)}" style="width:24px;height:24px;border-radius:4px;" onerror="handleImageError(this)">` : ''}
                        <a href="${r.rootdataurl || '#'}" target="_blank" style="color:var(--primary);">${r.name || '-'}</a>
                    </div>
                </td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${r.introduce || ''}">${r.introduce || '-'}</td>
                <td>${r.active ? '<span style="color:var(--success);">运营中</span>' : '<span style="color:var(--danger);">已停止</span>'}</td>
                <td>${r.created_at ? new Date(r.created_at).toLocaleString() : '-'}</td>
                <td>
                    ${r.entity_type === 1 ? `<button class="btn btn-sm btn-primary" onclick="fetchProjectDetail(${r.entity_id}, '${r.name}')">抓取详情</button>` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteTestResult(${r.id})">删除</button>
                </td>
            </tr>
        `).join('');

        // 更新分页控件
        updateTestPagination(data.pagination);

    } catch (e) {
        console.error('Failed to load test results:', e);
    }
}

function updateTestPagination(pagination) {
    const paginationDiv = document.getElementById('test-pagination');
    const pageNumbersDiv = document.getElementById('test-page-numbers');
    const prevBtn = document.getElementById('test-prev-btn');
    const nextBtn = document.getElementById('test-next-btn');
    const infoDiv = document.getElementById('test-pagination-info');

    if (pagination.total_pages <= 1) {
        paginationDiv.style.display = 'none';
        return;
    }

    paginationDiv.style.display = 'flex';

    // 更新按钮状态
    prevBtn.disabled = !pagination.has_prev;
    nextBtn.disabled = !pagination.has_next;

    // 生成页码按钮
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.total_pages, pagination.page + 2);

    let pageButtons = '';
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === pagination.page;
        pageButtons += `<button class="pagination-btn ${isActive ? 'active' : ''}" onclick="changeTestPage(${i})">${i}</button>`;
    }

    pageNumbersDiv.innerHTML = pageButtons;

    // 更新信息
    const startItem = (pagination.page - 1) * pagination.page_size + 1;
    const endItem = Math.min(pagination.page * pagination.page_size, pagination.total_count);

    infoDiv.textContent = `第 ${startItem}-${endItem} 条，共 ${pagination.total_count} 条`;
}

function changeTestPage(page) {
    loadTestResults(page);
}

async function deleteTestResult(id) {
    if (!confirm('确定要删除此记录吗？')) return;
    
    try {
        await api(`/api/test/search-results/${id}`, { method: 'DELETE' });
        showToast('删除成功');
        loadTestResults();
    } catch (e) {}
}

async function fetchProjectDetail(entityId, name) {
    if (!confirm(`确定要抓取 "${name}" 的详细信息吗？\n\n此操作将消耗 2 credits，并将项目保存到项目库。`)) {
        return;
    }
    
    try {
        showToast('正在抓取项目详情...', 'info');
        const data = await api('/api/projects/fetch', {
            method: 'POST',
            body: JSON.stringify({ project_id: entityId, mode: 'basic' })
        });
        showToast(data.message || `项目 "${name}" 抓取成功，可在投研报告中使用`);
    } catch (e) {
        showToast('抓取失败: ' + (e.message || '未知错误'), 'error');
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});
