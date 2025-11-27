// 全局变量
let currentTab = 'search';
let searchResults = [];
let currentDownloadBook = null;

// 页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    loadSources();
    loadSourcesForSearch();
});

// 切换标签页
function switchTab(tabName, event) {
    // 隐藏所有标签页
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // 移除所有按钮的激活状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 显示选中的标签页
    document.getElementById(`${tabName}-tab`).classList.add('active');
    if (event && event.target) {
        event.target.classList.add('active');
    }

    currentTab = tabName;

    // 加载标签页内容
    if (tabName === 'sources') {
        loadSources();
    } else if (tabName === 'tasks') {
        refreshTasks();
    } else if (tabName === 'files') {
        refreshFiles();
    }
}

// ==================== 书源管理 ====================
async function loadSources() {
    const loadingEl = document.getElementById('sources-loading');
    const listEl = document.getElementById('sources-list');

    loadingEl.style.display = 'block';
    listEl.innerHTML = '';

    try {
        const response = await fetch('/api/sources');
        const result = await response.json();

        loadingEl.style.display = 'none';

        if (result.success) {
            renderSources(result.data);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        loadingEl.style.display = 'none';
        showToast('加载书源失败: ' + error.message, 'error');
    }
}

function renderSources(sources) {
    const listEl = document.getElementById('sources-list');

    if (sources.length === 0) {
        listEl.innerHTML = '<p style="text-align: center; color: #888;">暂无书源</p>';
        return;
    }

    listEl.innerHTML = sources.map(source => `
        <div class="source-card" id="source-${source.id}">
            <div class="source-name">${source.id}. ${source.name}</div>
            <div class="source-url">${source.url}</div>
            ${source.comment ? `<div style="color: #888; font-size: 0.9em; margin: 10px 0;">${source.comment}</div>` : ''}
            <div style="margin-top: 10px;">
                <span class="source-badge ${source.search_enabled ? 'badge-success' : 'badge-warning'}">
                    ${source.search_enabled ? '✓ 支持搜索' : '✗ 不支持搜索'}
                </span>
                ${source.has_crawl_config ? '<span class="source-badge badge-success">✓ 限流配置</span>' : ''}
            </div>
        </div>
    `).join('');
}

// 检查所有书源
async function checkAllSources() {
    const loadingEl = document.getElementById('sources-loading');
    const summaryEl = document.getElementById('check-summary');
    const listEl = document.getElementById('sources-list');

    loadingEl.style.display = 'block';
    summaryEl.style.display = 'none';
    listEl.innerHTML = '';

    try {
        const response = await fetch('/api/sources/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();
        loadingEl.style.display = 'none';

        if (result.success) {
            renderCheckResults(result.data, result.summary);
            showToast('书源检查完成', 'success');
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        loadingEl.style.display = 'none';
        showToast('检查书源失败: ' + error.message, 'error');
    }
}

// 渲染检查结果
function renderCheckResults(results, summary) {
    const summaryEl = document.getElementById('check-summary');
    const listEl = document.getElementById('sources-list');

    // 显示汇总信息
    summaryEl.style.display = 'block';
    summaryEl.innerHTML = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin: 0 0 15px 0;">检查结果汇总</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px;">
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold;">${summary.total}</div>
                    <div style="opacity: 0.9;">总计</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #4caf50;">${summary.success}</div>
                    <div style="opacity: 0.9;">✓ 正常</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #ff9800;">${summary.warning}</div>
                    <div style="opacity: 0.9;">⚠ 警告</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #f44336;">${summary.error}</div>
                    <div style="opacity: 0.9;">✗ 错误</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #9e9e9e;">${summary.disabled}</div>
                    <div style="opacity: 0.9;">- 禁用</div>
                </div>
            </div>
        </div>
    `;

    // 显示详细结果
    if (results.length === 0) {
        listEl.innerHTML = '<p style="text-align: center; color: #888;">暂无书源</p>';
        return;
    }

    listEl.innerHTML = results.map(source => {
        let statusBadge = '';
        let statusClass = '';

        switch (source.status) {
            case 'success':
                statusBadge = `<span class="source-badge badge-success">✓ 正常 (${source.book_count}本)</span>`;
                statusClass = 'status-success';
                break;
            case 'warning':
                statusBadge = '<span class="source-badge badge-warning">⚠ 无结果</span>';
                statusClass = 'status-warning';
                break;
            case 'error':
                statusBadge = '<span class="source-badge badge-danger">✗ 错误</span>';
                statusClass = 'status-error';
                break;
            case 'disabled':
                statusBadge = '<span class="source-badge badge-secondary">- 禁用</span>';
                statusClass = 'status-disabled';
                break;
        }

        return `
            <div class="source-card ${statusClass}">
                <div class="source-name">${source.id}. ${source.name} ${statusBadge}</div>
                <div class="source-url">${source.url}</div>
                ${source.message ? `<div style="color: #666; font-size: 0.9em; margin: 10px 0;">${source.message}</div>` : ''}
            </div>
        `;
    }).join('');
}

// 加载书源到搜索下拉框
async function loadSourcesForSearch() {
    try {
        const response = await fetch('/api/sources');
        const result = await response.json();

        if (result.success) {
            const selectEl = document.getElementById('search-source');
            selectEl.innerHTML = '<option value="">所有书源</option>';

            result.data.forEach(source => {
                if (source.search_enabled) {
                    selectEl.innerHTML += `<option value="${source.id}">${source.name}</option>`;
                }
            });
        }
    } catch (error) {
        console.error('加载书源失败:', error);
    }
}

// ==================== 搜索功能 ====================
async function searchBooks() {
    const keyword = document.getElementById('search-keyword').value.trim();
    const sourceId = document.getElementById('search-source').value;

    if (!keyword) {
        showToast('请输入搜索关键词', 'error');
        return;
    }

    const loadingEl = document.getElementById('search-loading');
    const resultsEl = document.getElementById('search-results');

    loadingEl.style.display = 'block';
    resultsEl.innerHTML = '';

    // 使用SSE流式接口
    try {
        // 创建进度显示区域
        const progressDiv = document.createElement('div');
        progressDiv.className = 'search-progress';
        progressDiv.style.marginBottom = '20px';
        resultsEl.appendChild(progressDiv);

        // 使用fetch发送POST请求获取stream
        const response = await fetch('/api/search/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                keyword: keyword,
                source_id: sourceId ? parseInt(sourceId) : null
            })
        });

        if (!response.ok) {
            throw new Error('搜索请求失败');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let allBooks = [];
        let totalSources = 0;
        let completed = 0;

        // 读取流
        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // 保留最后一个不完整的部分

            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) {
                    continue;
                }

                const data = JSON.parse(line.substring(6));

                switch (data.type) {
                    case 'start':
                        totalSources = data.total;
                        progressDiv.innerHTML = `
                            <div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">
                                <div style="margin-bottom: 10px;">正在搜索关键词: <strong>${data.keyword}</strong></div>
                                <div style="margin-bottom: 10px;">总计书源: ${data.total} 个</div>
                                <div class="progress-bar">
                                    <div class="progress-fill" id="search-progress-bar" style="width: 0%"></div>
                                </div>
                                <div id="search-status" style="margin-top: 10px; color: #666;"></div>
                            </div>
                        `;
                        break;

                    case 'searching':
                        document.getElementById('search-status').textContent = `正在搜索: ${data.source}...`;
                        break;

                    case 'result':
                        completed = data.completed;
                        const progress = (completed / totalSources * 100).toFixed(0);
                        document.getElementById('search-progress-bar').style.width = `${progress}%`;
                        document.getElementById('search-status').innerHTML = `
                            ${data.source}: 找到 <span style="color: #4caf50; font-weight: bold;">${data.count}</span> 本书 (${completed}/${totalSources})
                        `;

                        // 实时显示结果
                        allBooks.push(...data.books);
                        renderSearchResults(allBooks);
                        searchResults = allBooks;
                        break;

                    case 'error_source':
                        completed = data.completed;
                        const errorProgress = (completed / totalSources * 100).toFixed(0);
                        document.getElementById('search-progress-bar').style.width = `${errorProgress}%`;
                        document.getElementById('search-status').innerHTML = `
                            ${data.source}: <span style="color: #f44336;">搜索失败</span> - ${data.error.substring(0, 50)} (${completed}/${totalSources})
                        `;
                        break;

                    case 'complete':
                        loadingEl.style.display = 'none';
                        progressDiv.innerHTML = `
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px;">
                                ✓ 搜索完成！共找到 <strong>${data.total_books}</strong> 本书
                            </div>
                        `;
                        allBooks = data.books;
                        renderSearchResults(allBooks);
                        searchResults = allBooks;
                        break;

                    case 'error':
                        loadingEl.style.display = 'none';
                        showToast('搜索失败: ' + data.message, 'error');
                        progressDiv.remove();
                        break;
                }
            }
        }
    } catch (error) {
        loadingEl.style.display = 'none';
        showToast('搜索失败: ' + error.message, 'error');
    }
}

// ==================== 阅读器功能 ====================
function openReader(index) {
    const book = searchResults[index];
    if (!book) {
        showToast('无效的书籍索引', 'error');
        return;
    }

    // 构建阅读器URL
    const readerUrl = `/reader/${book.source_id}/${encodeURIComponent(book.url)}`;
    
    // 在新标签页打开阅读器
    window.open(readerUrl, '_blank');
}

function renderSearchResults(books) {
    const resultsEl = document.getElementById('search-results');

    // 查找或创建结果容器
    let booksContainer = resultsEl.querySelector('.books-container');
    if (!booksContainer) {
        booksContainer = document.createElement('div');
        booksContainer.className = 'books-container';
        resultsEl.appendChild(booksContainer);
    }

    if (books.length === 0) {
        booksContainer.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">未找到相关书籍</p>';
        return;
    }

    booksContainer.innerHTML = books.map((book, index) => `
        <div class="result-item">
            <div class="result-header">
                <div>
                    <div class="result-title">${book.book_name}</div>
                    <div class="result-author">作者: ${book.author}</div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-success" onclick="openReader(${index})" style="background: #28a745;">📖 阅读</button>
                    <button class="btn btn-primary" onclick="openDownloadModal(${index})">下载</button>
                </div>
            </div>
            <div class="result-meta">
                <span>📚 书源: ${book.source_name}</span>
                ${book.category ? `<span>🏷️ ${book.category}</span>` : ''}
                ${book.status ? `<span>📊 ${book.status}</span>` : ''}
                ${book.word_count ? `<span>📝 ${book.word_count}</span>` : ''}
            </div>
            ${book.latest_chapter ? `<div style="margin-top: 10px; color: #666;">最新: ${book.latest_chapter}</div>` : ''}
        </div>
    `).join('');
}

// ==================== 下载功能 ====================
function openDownloadModal(index) {
    const book = searchResults[index];
    currentDownloadBook = book;

    document.getElementById('download-url').value = book.url;
    document.getElementById('download-book-name').value = book.book_name;
    document.getElementById('download-author').value = book.author;
    document.getElementById('download-source-id').value = book.source_id;
    document.getElementById('download-start').value = 1;
    document.getElementById('download-end').value = -1;

    document.getElementById('download-modal').classList.add('active');
}

function closeDownloadModal() {
    document.getElementById('download-modal').classList.remove('active');
    currentDownloadBook = null;
}

async function startDownload() {
    const bookUrl = document.getElementById('download-url').value;
    const sourceId = parseInt(document.getElementById('download-source-id').value);
    const startChapter = parseInt(document.getElementById('download-start').value);
    const endChapter = parseInt(document.getElementById('download-end').value);
    const format = document.getElementById('download-format').value;

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                book_url: bookUrl,
                source_id: sourceId,
                start_chapter: startChapter,
                end_chapter: endChapter,
                format: format
            })
        });

        const result = await response.json();

        if (result.success) {
            showToast('下载任务已创建', 'success');
            closeDownloadModal();

            // 切换到任务标签页
            switchTab('tasks');

            // 刷新任务列表
            setTimeout(() => refreshTasks(), 500);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('创建下载任务失败: ' + error.message, 'error');
    }
}

// ==================== 任务管理 ====================
async function refreshTasks() {
    const listEl = document.getElementById('tasks-list');

    try {
        const response = await fetch('/api/tasks');
        const result = await response.json();

        if (result.success) {
            renderTasks(result.data);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('获取任务列表失败: ' + error.message, 'error');
    }
}

function renderTasks(tasks) {
    const listEl = document.getElementById('tasks-list');

    if (tasks.length === 0) {
        listEl.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">暂无下载任务</p>';
        return;
    }

    // 按创建时间降序排序
    tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    listEl.innerHTML = tasks.map(task => `
        <div class="task-item">
            <div class="task-header">
                <div>
                    <div style="font-weight: bold; font-size: 1.1em;">
                        ${task.book_name || '未知书籍'}
                        ${task.author ? `<span style="color: #666; font-size: 0.9em;">（${task.author}）</span>` : ''}
                    </div>
                    <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
                        书源: ${task.source_name} | 创建于: ${new Date(task.created_at).toLocaleString()}
                    </div>
                </div>
                <span class="task-status status-${task.status}">${getStatusText(task.status)}</span>
            </div>
            ${task.status === 'downloading' ? `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${task.progress}%"></div>
                </div>
                <div style="text-align: center; color: #666; font-size: 0.9em;">
                    ${task.downloaded_chapters}/${task.total_chapters} 章节
                </div>
            ` : ''}
            ${task.error ? `<div style="color: #f44336; margin-top: 10px;">错误: ${task.error}</div>` : ''}
            <div style="margin-top: 10px;">
                <button class="btn btn-danger" onclick="deleteTask('${task.id}')">删除</button>
            </div>
        </div>
    `).join('');
}

function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'downloading': '下载中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗？')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showToast('任务已删除', 'success');
            refreshTasks();
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('删除任务失败: ' + error.message, 'error');
    }
}

// ==================== 文件管理 ====================
async function refreshFiles() {
    const listEl = document.getElementById('files-list');

    try {
        const response = await fetch('/api/files');
        const result = await response.json();

        if (result.success) {
            renderFiles(result.data);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('获取文件列表失败: ' + error.message, 'error');
    }
}

function renderFiles(files) {
    const listEl = document.getElementById('files-list');

    if (files.length === 0) {
        listEl.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">暂无已下载文件</p>';
        return;
    }

    listEl.innerHTML = files.map(file => `
        <div class="file-item">
            <div class="file-info">
                <div class="file-name">📄 ${file.name}</div>
                <div class="file-meta">
                    大小: ${formatFileSize(file.size)} |
                    修改于: ${new Date(file.modified_at).toLocaleString()}
                </div>
            </div>
            <div>
                <a href="/api/files/${encodeURIComponent(file.name)}" download class="btn btn-primary">下载</a>
            </div>
        </div>
    `).join('');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
}

// ==================== 工具函数 ====================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s reverse';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// 支持回车搜索
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('search-keyword').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchBooks();
        }
    });
});

// 自动刷新下载任务（如果在任务标签页）
setInterval(() => {
    if (currentTab === 'tasks') {
        refreshTasks();
    }
}, 5000);  // 每 5 秒刷新一次
