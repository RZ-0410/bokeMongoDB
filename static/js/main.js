// 全局变量
let currentPage = 1;
let isLoading = false;

// 显示加载动画
function showLoading() {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner show';
    spinner.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">加载中...</span>
        </div>
    `;
    document.body.appendChild(spinner);
}

// 隐藏加载动画
function hideLoading() {
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// 显示 Toast 通知
function showToast(message, type = 'info') {
    // 创建 toast 容器
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    // 创建 toast
    const toast = document.createElement('div');
    toast.className = `toast show align-items-center text-white bg-${getToastType(type)} border-0`;
    toast.setAttribute('role', 'alert');
    
    const icon = getToastIcon(type);
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${icon} me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // 自动移除
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
    
    // 点击关闭
    toast.querySelector('.btn-close').addEventListener('click', () => {
        toast.remove();
    });
}

// 获取 toast 类型样式
function getToastType(type) {
    const types = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return types[type] || 'info';
}

// 获取 toast 图标
function getToastIcon(type) {
    const icons = {
        'success': 'bi-check-circle-fill',
        'error': 'bi-x-circle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'info': 'bi-info-circle-fill'
    };
    return icons[type] || 'bi-info-circle-fill';
}

// 显示搜索历史
function showSearchHistory() {
    const modal = new bootstrap.Modal(document.getElementById('searchHistoryModal'));
    modal.show();
    
    // 加载搜索历史
    loadSearchHistory();
}

// 加载搜索历史
function loadSearchHistory() {
    const content = document.getElementById('searchHistoryContent');
    
    fetch('/search_history')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.history.length > 0) {
                let html = `
                    <div class="list-group">
                        ${data.history.map(item => `
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <a href="/search?q=${encodeURIComponent(item.keyword)}" 
                                       class="text-decoration-none">
                                        <i class="bi bi-search me-2"></i>${item.keyword}
                                    </a>
                                    <br>
                                    <small class="text-muted">
                                        ${new Date(item.timestamp).toLocaleString()}
                                    </small>
                                </div>
                                <button class="btn btn-sm btn-outline-danger" 
                                        onclick="deleteSearchHistory('${item._id}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        `).join('')}
                    </div>
                `;
                content.innerHTML = html;
            } else {
                content.innerHTML = `
                    <div class="text-center py-4">
                        <i class="bi bi-clock-history display-4 text-muted"></i>
                        <p class="text-muted mt-2">暂无搜索历史</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            content.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-exclamation-circle display-4 text-danger"></i>
                    <p class="text-danger mt-2">加载失败</p>
                </div>
            `;
        });
}

// 删除搜索历史
function deleteSearchHistory(historyId) {
    if (!confirm('确定要删除这条搜索历史吗？')) {
        return;
    }
    
    fetch(`/delete_search_history/${historyId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('已删除', 'success');
            loadSearchHistory(); // 重新加载历史记录
        } else {
            showToast('删除失败', 'error');
        }
    })
    .catch(error => {
        showToast('网络错误', 'error');
    });
}

// 平滑滚动到顶部
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 平滑滚动到指定元素
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// 格式化时间
function formatTime(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diff = now - time;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) {
        return '刚刚';
    } else if (minutes < 60) {
        return `${minutes}分钟前`;
    } else if (hours < 24) {
        return `${hours}小时前`;
    } else if (days < 7) {
        return `${days}天前`;
    } else {
        return time.toLocaleDateString();
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// 检查元素是否在视口中
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// 添加滚动动画
function addScrollAnimations() {
    const elements = document.querySelectorAll('.scroll-animate');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    elements.forEach(element => {
        observer.observe(element);
    });
}

// 复制文本到剪贴板
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('已复制到剪贴板', 'success');
        }).catch(() => {
            fallbackCopyTextToClipboard(text);
        });
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

// 备用复制方法
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('已复制到剪贴板', 'success');
    } catch (err) {
        showToast('复制失败', 'error');
    }
    
    document.body.removeChild(textArea);
}

// 本地存储操作
const Storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('存储失败:', e);
        }
    },
    
    get: function(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (e) {
            console.error('读取失败:', e);
            return null;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('删除失败:', e);
        }
    },
    
    clear: function() {
        try {
            localStorage.clear();
        } catch (e) {
            console.error('清空失败:', e);
        }
    }
};

// 主题切换
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    body.setAttribute('data-theme', newTheme);
    Storage.set('theme', newTheme);
    
    // 更新主题切换按钮
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = newTheme === 'dark' ? 
            '<i class="bi bi-sun"></i>' : 
            '<i class="bi bi-moon"></i>';
    }
    
    showToast(`已切换到${newTheme === 'dark' ? '深色' : '浅色'}主题`, 'success');
}

// 加载保存的主题
function loadTheme() {
    const savedTheme = Storage.get('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    
    // 更新主题切换按钮
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = savedTheme === 'dark' ? 
            '<i class="bi bi-sun"></i>' : 
            '<i class="bi bi-moon"></i>';
    }
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 添加滚动动画
    addScrollAnimations();
    
    // 加载主题
    loadTheme();
    
    // 添加回到顶部按钮
    const backToTop = document.createElement('button');
    backToTop.className = 'btn btn-primary btn-sm position-fixed bottom-0 end-0 m-3';
    backToTop.style.display = 'none';
    backToTop.style.zIndex = '999';
    backToTop.innerHTML = '<i class="bi bi-arrow-up"></i>';
    backToTop.onclick = scrollToTop;
    document.body.appendChild(backToTop);
    
    // 监听滚动事件
    window.addEventListener('scroll', throttle(() => {
        if (window.pageYOffset > 300) {
            backToTop.style.display = 'block';
        } else {
            backToTop.style.display = 'none';
        }
    }, 100));
    
    // 添加键盘快捷键
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K 聚焦搜索框
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // ESC 关闭模态框
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal.show');
            if (modal) {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
            }
        }
    });
    
    // 添加工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 添加弹出提示
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// 页面卸载前执行
window.addEventListener('beforeunload', function() {
    // 保存用户偏好设置
    const preferences = {
        lastVisit: new Date().toISOString(),
        visitCount: (Storage.get('visitCount') || 0) + 1
    };
    Storage.set('preferences', preferences);
});

// 导出全局函数供其他脚本使用
window.utils = {
    showLoading,
    hideLoading,
    showToast,
    scrollToTop,
    scrollToElement,
    formatTime,
    debounce,
    throttle,
    isInViewport,
    copyToClipboard,
    Storage,
    toggleTheme,
    loadTheme
};