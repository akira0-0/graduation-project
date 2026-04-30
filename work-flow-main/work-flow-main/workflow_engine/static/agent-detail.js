// 智能体节点详情展示功能

let currentAgentNode = null;

// 显示智能体详情模态框
function showAgentDetail(nodeId) {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;
    
    currentAgentNode = node;
    
    // 设置模态框标题
    const icons = {
        'DataCollectionAgent': 'fa-database',
        'SentimentAgent': 'fa-heart',
        'ReportAgent': 'fa-file-alt',
        'FilterAgent': 'fa-filter'
    };
    
    document.getElementById('agent-detail-icon').className = `fas ${icons[node.type] || 'fa-robot'}`;
    document.getElementById('agent-detail-name').textContent = node.config.title || '智能体节点';
    document.getElementById('agent-detail-title').textContent = `${node.config.title || '智能体节点'} - 详情`;
    
    // 渲染配置内容
    renderAgentConfig(node);
    
    // 渲染输入输出内容
    renderAgentInput(node);
    renderAgentOutput(node);
    renderAgentStats(node);
    
    // 显示模态框
    document.getElementById('agent-detail-modal').classList.remove('hidden');
    
    // 默认显示配置标签
    showAgentDetailTab('config');
}

// 隐藏智能体详情模态框
function hideAgentDetailModal() {
    document.getElementById('agent-detail-modal').classList.add('hidden');
    currentAgentNode = null;
}

// 切换标签页
function showAgentDetailTab(tabName) {
    // 隐藏所有面板
    document.querySelectorAll('.agent-detail-panel').forEach(panel => {
        panel.classList.add('hidden');
    });
    
    // 重置所有标签样式
    document.querySelectorAll('.agent-detail-tab').forEach(tab => {
        tab.classList.remove('active', 'text-blue-600', 'bg-white', 'border-blue-600');
        tab.classList.add('text-gray-600', 'border-transparent');
    });
    
    // 显示选中的面板
    const panel = document.getElementById(`panel-agent-${tabName}`);
    const tab = document.getElementById(`tab-agent-${tabName}`);
    
    if (panel && tab) {
        panel.classList.remove('hidden');
        tab.classList.add('active', 'text-blue-600', 'bg-white', 'border-blue-600');
        tab.classList.remove('text-gray-600', 'border-transparent');
    }
}

// 渲染配置内容
function renderAgentConfig(node) {
    const configContent = document.getElementById('agent-config-content');
    let html = '';
    
    if (node.type === 'DataCollectionAgent') {
        html = `
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-search mr-2 text-blue-600"></i>数据主题
                    </label>
                    <input type="text" id="agent-config-topic" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" 
                           value="${node.config.params.topic || ''}" placeholder="例如: 用户反馈, 市场趋势">
                    <p class="text-xs text-gray-500 mt-1">设置数据收集的主题关键词</p>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-globe mr-2 text-blue-600"></i>数据来源
                    </label>
                    <div class="grid grid-cols-2 gap-2">
                        <label class="flex items-center gap-2 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" id="agent-source-twitter" ${node.config.params.sources?.includes('twitter') ? 'checked' : ''} class="rounded border-gray-300 text-blue-600">
                            <i class="fab fa-twitter text-blue-400"></i>
                            <span>Twitter</span>
                        </label>
                        <label class="flex items-center gap-2 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" id="agent-source-news" ${node.config.params.sources?.includes('news') ? 'checked' : ''} class="rounded border-gray-300 text-blue-600">
                            <i class="fas fa-newspaper text-gray-600"></i>
                            <span>新闻</span>
                        </label>
                        <label class="flex items-center gap-2 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" id="agent-source-social" ${node.config.params.sources?.includes('social_media') ? 'checked' : ''} class="rounded border-gray-300 text-blue-600">
                            <i class="fas fa-users text-purple-500"></i>
                            <span>社交媒体</span>
                        </label>
                        <label class="flex items-center gap-2 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" id="agent-source-kb" ${node.config.params.sources?.includes('internal_knowledge_base') ? 'checked' : ''} class="rounded border-gray-300 text-blue-600">
                            <i class="fas fa-book text-green-600"></i>
                            <span>知识库</span>
                        </label>
                    </div>
                </div>
            </div>
        `;
    } else if (node.type === 'SentimentAgent') {
        html = `
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-database mr-2 text-pink-600"></i>待分析数据
                    </label>
                    <textarea id="agent-config-data" rows="3" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500" 
                              placeholder="输入要分析的数据或引用上游节点输出">${node.config.params.data || ''}</textarea>
                </div>
                <div>
                    <label class="flex items-center gap-2 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                        <input type="checkbox" id="agent-config-memory" ${node.config.params.use_memory ? 'checked' : ''} class="rounded border-gray-300 text-pink-600">
                        <i class="fas fa-brain text-pink-500"></i>
                        <span class="text-sm font-medium text-gray-700">使用记忆功能</span>
                    </label>
                </div>
            </div>
        `;
    } else if (node.type === 'FilterAgent') {
        html = `
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-database mr-2 text-indigo-600"></i>待过滤数据
                    </label>
                    <textarea id="agent-config-data" rows="3" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" 
                              placeholder="输入要过滤的数据">${node.config.params.data || ''}</textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-filter mr-2 text-indigo-600"></i>过滤规则
                    </label>
                    <textarea id="agent-config-filters" rows="5" class="w-full px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm" 
                              placeholder='{"keywords": ["重要"]}'>${JSON.stringify(node.config.params.filters || {}, null, 2)}</textarea>
                </div>
            </div>
        `;
    } else if (node.type === 'ReportAgent') {
        html = `
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-file-alt mr-2 text-green-600"></i>报告类型
                    </label>
                    <select id="agent-config-report-type" class="w-full px-4 py-2 border border-gray-300 rounded-lg">
                        <option value="sentiment_analysis" ${node.config.params.report_type === 'sentiment_analysis' ? 'selected' : ''}>情感分析报告</option>
                        <option value="data_collection" ${node.config.params.report_type === 'data_collection' ? 'selected' : ''}>数据收集报告</option>
                        <option value="custom" ${node.config.params.report_type === 'custom' ? 'selected' : ''}>自定义报告</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        <i class="fas fa-palette mr-2 text-green-600"></i>报告模板
                    </label>
                    <select id="agent-config-template" class="w-full px-4 py-2 border border-gray-300 rounded-lg">
                        <option value="default" ${node.config.params.template === 'default' ? 'selected' : ''}>默认模板</option>
                        <option value="detailed" ${node.config.params.template === 'detailed' ? 'selected' : ''}>详细模板</option>
                        <option value="summary" ${node.config.params.template === 'summary' ? 'selected' : ''}>摘要模板</option>
                    </select>
                </div>
            </div>
        `;
    }
    
    configContent.innerHTML = html;
}

// 渲染输入数据
function renderAgentInput(node) {
    const inputContent = document.getElementById('agent-input-content');
    
    if (!node.executionOutput) {
        inputContent.innerHTML = `
            <div class="text-center py-12">
                <i class="fas fa-inbox text-4xl text-gray-300 mb-4"></i>
                <p class="text-gray-500">尚未执行，暂无输入数据</p>
                <p class="text-sm text-gray-400 mt-2">执行工作流后可查看输入数据</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="space-y-4">';
    
    if (node.type === 'DataCollectionAgent') {
        html += `
            <div class="bg-gray-50 rounded-lg p-4">
                <h4 class="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <i class="fas fa-search text-blue-600"></i>
                    收集参数
                </h4>
                <div class="space-y-2">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-medium text-gray-600">主题:</span>
                        <span class="text-sm text-gray-800">${node.config.params.topic || '未设置'}</span>
                    </div>
                    <div class="flex items-start gap-2">
                        <span class="text-sm font-medium text-gray-600">来源:</span>
                        <div class="flex flex-wrap gap-1">
                            ${(node.config.params.sources || []).map(source => `
                                <span class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">${source}</span>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="bg-gray-50 rounded-lg p-4">
                <h4 class="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <i class="fas fa-file-import text-blue-600"></i>
                    输入数据源
                </h4>
                <pre class="text-sm bg-white p-3 rounded border border-gray-200 overflow-auto max-h-64">${JSON.stringify(node.executionOutput.input || '无输入数据', null, 2)}</pre>
            </div>
        `;
    }
    
    html += '</div>';
    inputContent.innerHTML = html;
}

// 渲染输出结果
function renderAgentOutput(node) {
    const outputContent = document.getElementById('agent-output-content');
    
    if (!node.executionOutput) {
        outputContent.innerHTML = `
            <div class="text-center py-12">
                <i class="fas fa-clipboard-list text-4xl text-gray-300 mb-4"></i>
                <p class="text-gray-500">尚未执行，暂无输出结果</p>
                <p class="text-sm text-gray-400 mt-2">执行工作流后可查看输出结果</p>
            </div>
        `;
        return;
    }
    
    const output = node.executionOutput;
    let html = '<div class="space-y-4">';
    
    if (node.type === 'DataCollectionAgent') {
        const items = output.items || output.data || [];
        html += `
            <div class="bg-blue-50 rounded-lg p-4 mb-4">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="font-semibold text-blue-800">
                        <i class="fas fa-database mr-2"></i>收集结果
                    </h4>
                    <span class="px-2 py-1 bg-blue-600 text-white text-xs rounded">共 ${Array.isArray(items) ? items.length : 0} 条</span>
                </div>
            </div>
            <div class="space-y-2 max-h-96 overflow-y-auto">
                ${Array.isArray(items) ? items.slice(0, 10).map((item, index) => `
                    <div class="bg-white border border-gray-200 rounded-lg p-3">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs font-medium text-blue-600">#${index + 1}</span>
                            <span class="text-xs text-gray-500">${item.source || '未知来源'}</span>
                        </div>
                        <p class="text-sm text-gray-700 mb-2">${item.title || item.content?.substring(0, 100) || '无标题'}</p>
                        ${item.url ? `<a href="${item.url}" target="_blank" class="text-xs text-blue-500 hover:underline">${item.url}</a>` : ''}
                    </div>
                `).join('') : '<p class="text-gray-500">无数据</p>'}
            </div>
        `;
    } else if (node.type === 'SentimentAgent') {
        const results = output.results || output.sentiments || [];
        const summary = output.summary || {};
        
        html += `
            <div class="grid grid-cols-3 gap-4 mb-4">
                <div class="bg-green-50 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-green-600">${summary.positive || 0}</div>
                    <div class="text-xs text-green-700">正面</div>
                </div>
                <div class="bg-gray-50 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-gray-600">${summary.neutral || 0}</div>
                    <div class="text-xs text-gray-700">中性</div>
                </div>
                <div class="bg-red-50 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-red-600">${summary.negative || 0}</div>
                    <div class="text-xs text-red-700">负面</div>
                </div>
            </div>
            <div class="space-y-2 max-h-64 overflow-y-auto">
                ${Array.isArray(results) ? results.map((result, index) => `
                    <div class="bg-white border border-gray-200 rounded-lg p-3">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs font-medium text-gray-600">#${index + 1}</span>
                            <span class="px-2 py-1 text-xs rounded ${
                                result.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                                result.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-700'
                            }">${result.sentiment || '中性'}</span>
                        </div>
                        <p class="text-sm text-gray-700 mb-1">${result.text?.substring(0, 80) || '无文本'}...</p>
                    </div>
                `).join('') : '<p class="text-gray-500">无分析结果</p>'}
            </div>
        `;
    } else if (node.type === 'FilterAgent') {
        const filteredData = output.filtered_data || output.items || [];
        const originalCount = output.original_count || 0;
        const filteredCount = Array.isArray(filteredData) ? filteredData.length : 0;
        
        html += `
            <div class="bg-indigo-50 rounded-lg p-4 mb-4">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="font-semibold text-indigo-800">
                        <i class="fas fa-filter mr-2"></i>过滤结果
                    </h4>
                    <div class="flex items-center gap-2 text-sm">
                        <span class="text-gray-600">${originalCount} 条</span>
                        <i class="fas fa-arrow-right text-indigo-600"></i>
                        <span class="font-semibold text-indigo-600">${filteredCount} 条</span>
                    </div>
                </div>
            </div>
            <div class="space-y-2 max-h-64 overflow-y-auto">
                ${Array.isArray(filteredData) && filteredData.length > 0 ? filteredData.slice(0, 10).map((item, index) => `
                    <div class="bg-white border border-gray-200 rounded-lg p-3">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs font-medium text-indigo-600">#${index + 1}</span>
                            ${item.sentiment ? `<span class="px-2 py-1 text-xs rounded ${
                                item.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                                item.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-700'
                            }">${item.sentiment}</span>` : ''}
                        </div>
                        <p class="text-sm text-gray-700">${item.title || item.content?.substring(0, 100) || '无内容'}</p>
                    </div>
                `).join('') : '<p class="text-gray-500">无过滤结果</p>'}
            </div>
        `;
    } else if (node.type === 'ReportAgent') {
        html += `
            <div class="bg-green-50 rounded-lg p-4 mb-4">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="font-semibold text-green-800">
                        <i class="fas fa-file-alt mr-2"></i>生成的报告
                    </h4>
                    <button onclick="downloadReport()" class="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700">
                        <i class="fas fa-download mr-1"></i>下载
                    </button>
                </div>
            </div>
            <div class="bg-white border border-gray-200 rounded-lg p-4 max-h-96 overflow-y-auto">
                <pre class="text-sm text-gray-700 whitespace-pre-wrap">${output.report || output.content || JSON.stringify(output, null, 2)}</pre>
            </div>
        `;
    } else {
        html += `
            <div class="bg-gray-50 rounded-lg p-4">
                <h4 class="font-semibold text-gray-800 mb-3">原始输出</h4>
                <pre class="text-sm bg-white p-3 rounded border border-gray-200 overflow-auto max-h-96">${JSON.stringify(output, null, 2)}</pre>
            </div>
        `;
    }
    
    html += '</div>';
    outputContent.innerHTML = html;
}

// 渲染统计信息
function renderAgentStats(node) {
    const statsContent = document.getElementById('agent-stats-content');
    
    if (!node.executionOutput) {
        statsContent.innerHTML = `
            <div class="text-center py-12">
                <i class="fas fa-chart-pie text-4xl text-gray-300 mb-4"></i>
                <p class="text-gray-500">尚未执行，暂无统计信息</p>
                <p class="text-sm text-gray-400 mt-2">执行工作流后可查看统计信息</p>
            </div>
        `;
        return;
    }
    
    const output = node.executionOutput;
    let html = '<div class="space-y-4">';
    
    html += `
        <div class="grid grid-cols-2 gap-4">
            <div class="bg-blue-50 rounded-lg p-4">
                <div class="text-sm text-blue-600 mb-1">执行状态</div>
                <div class="text-lg font-semibold text-blue-800">
                    <i class="fas fa-check-circle mr-1"></i>成功
                </div>
            </div>
            <div class="bg-green-50 rounded-lg p-4">
                <div class="text-sm text-green-600 mb-1">节点ID</div>
                <div class="text-sm font-semibold text-green-800">${node.id}</div>
            </div>
        </div>
    `;
    
    if (node.type === 'DataCollectionAgent') {
        const items = output.items || output.data || [];
        html += `
            <div class="bg-white border border-gray-200 rounded-lg p-4">
                <h4 class="font-semibold text-gray-800 mb-3">
                    <i class="fas fa-chart-bar text-blue-600 mr-2"></i>数据统计
                </h4>
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-600">收集总数</span>
                        <span class="text-sm font-semibold text-gray-800">${Array.isArray(items) ? items.length : 0} 条</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-600">数据来源</span>
                        <span class="text-sm font-semibold text-gray-800">${(node.config.params.sources || []).length} 个</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    statsContent.innerHTML = html;
}

// 保存智能体配置
function saveAgentConfig() {
    if (!currentAgentNode) return;
    
    if (currentAgentNode.type === 'DataCollectionAgent') {
        currentAgentNode.config.params.topic = document.getElementById('agent-config-topic').value;
        const sources = [];
        if (document.getElementById('agent-source-twitter').checked) sources.push('twitter');
        if (document.getElementById('agent-source-news').checked) sources.push('news');
        if (document.getElementById('agent-source-social').checked) sources.push('social_media');
        if (document.getElementById('agent-source-kb').checked) sources.push('internal_knowledge_base');
        currentAgentNode.config.params.sources = sources;
    } else if (currentAgentNode.type === 'SentimentAgent') {
        currentAgentNode.config.params.data = document.getElementById('agent-config-data').value;
        currentAgentNode.config.params.use_memory = document.getElementById('agent-config-memory').checked;
    } else if (currentAgentNode.type === 'FilterAgent') {
        currentAgentNode.config.params.data = document.getElementById('agent-config-data').value;
        try {
            currentAgentNode.config.params.filters = JSON.parse(document.getElementById('agent-config-filters').value);
        } catch (e) {
            alert('过滤规则JSON格式错误');
            return;
        }
    } else if (currentAgentNode.type === 'ReportAgent') {
        currentAgentNode.config.params.report_type = document.getElementById('agent-config-report-type').value;
        currentAgentNode.config.params.template = document.getElementById('agent-config-template').value;
    }
    
    addLog('success', `保存智能体配置: ${currentAgentNode.config.title}`);
    renderCanvas();
}

// 下载报告
function downloadReport() {
    if (!currentAgentNode || !currentAgentNode.executionOutput) return;
    
    const report = currentAgentNode.executionOutput.report || currentAgentNode.executionOutput.content || '';
    const blob = new Blob([report], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${currentAgentNode.id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}