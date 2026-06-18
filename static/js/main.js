/**
 * 光核安利漂流瓶 v5 — 前端交互
 * 投递/打捞动画 · CSRF · Toast · 安利墙 · 任务
 */

/* ── CSRF ─────────────────────────────── */
function getCSRFToken(){
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}
function apiHeaders(){
    return {'Content-Type': 'application/json', 'X-CSRF-Token': getCSRFToken()};
}

/* ── Toast 通知 ───────────────────────── */
function showToast(msg, type){
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    if (!container){
        container = document.createElement('div');
        container.className = 'toast-container';
        container.id = 'toastContainer';
        document.body.appendChild(container);
    }
    var el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.innerHTML = msg + '<span class="toast-close" onclick="this.parentElement.remove()">×</span>';
    container.appendChild(el);
    setTimeout(function(){
        el.style.opacity = '0';
        el.style.transform = 'translateY(-8px)';
        setTimeout(function(){ el.remove(); }, 400);
    }, 5000);
}

/* ── 规则弹窗 ─────────────────────────── */
function showRules(){
    var modal = document.getElementById('rulesModal');
    if (modal){
        modal.style.display = 'flex';
        // sessionStorage：标签页关闭即重置，下次登录再弹
        try { sessionStorage.setItem('rules_shown', '1'); } catch(e) {}
    }
}
function closeRules(){
    var modal = document.getElementById('rulesModal');
    if (modal) modal.style.display = 'none';
}

/* ── 二维码放大预览 ───────────────────── */
function zoomQR(card){
    var img = card.querySelector('img');
    if (!img) return;
    var overlay = document.getElementById('qrZoomOverlay');
    var zoomImg = document.getElementById('qrZoomImg');
    if (overlay && zoomImg){
        zoomImg.src = img.src;
        zoomImg.alt = img.alt;
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}
function closeZoomQR(){
    var overlay = document.getElementById('qrZoomOverlay');
    if (overlay){
        overlay.style.display = 'none';
        document.body.style.overflow = '';
    }
}

/* ── 工具 ─────────────────────────────── */
function esc(t){ if (!t) return ''; var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

/* ── 背景切换动画 ─────────────────────── */
var bgPause = window._transitionPause || 1000;
var bgWhite = window._whiteScreenMs || 1000;

function hideUI(){ document.body.classList.add('in-transition'); }
function showUI(){ document.body.classList.remove('in-transition'); }
function setBg(name){
    document.body.classList.remove('bg-with-bottle', 'bg-no-bottle');
    if (name) document.body.classList.add(name);
}
function whiteScreen(on, callback){
    var s = document.getElementById('transitionShroud');
    if (!s){ if(callback)callback(); return; }
    if (on){ s.classList.add('on'); setTimeout(function(){ if(callback)callback(); }, bgWhite); }
    else { s.classList.remove('on'); if(callback)callback(); }
}

/**
 * 投递动画：隐藏 UI → "有瓶子"背景 → 停留 → 白屏 → 默认背景 → 恢复 UI → 回调
 */
function animateThrow(callback){
    hideUI();
    setTimeout(function(){
        setBg('bg-with-bottle');
        setTimeout(function(){
            whiteScreen(true, function(){
                setBg(null);
                whiteScreen(false, function(){
                    showUI();
                    if (callback) callback();
                });
            });
        }, bgPause);
    }, 200);
}

/**
 * 打捞动画：隐藏 UI → 默认背景 → 停留 → 白屏 → "有瓶子"背景 → 停留 → 恢复 UI+结果 → 自动切回默认
 */
function animateSalvage(callback){
    hideUI();
    setTimeout(function(){
        setBg('bg-no-bottle');
        setTimeout(function(){
            whiteScreen(true, function(){
                whiteScreen(false);
                setBg('bg-with-bottle');
                setTimeout(function(){
                    showUI();
                    if (callback) callback();
                    // 自动切回默认背景
                    setTimeout(function(){ setBg(null); }, 1200);
                }, bgPause);
            });
        }, bgPause);
    }, 200);
}

/* ── 初始化 ───────────────────────────── */
document.addEventListener('DOMContentLoaded', function(){
    // Toast 自动消失
    document.querySelectorAll('.toast').forEach(function(m){
        setTimeout(function(){
            m.style.opacity = '0';
            m.style.transform = 'translateY(-8px)';
            setTimeout(function(){ m.remove(); }, 400);
        }, 5000);
    });

    // 全局图片加载失败兜底（安利墙/瓶子详情/打捞结果等动态渲染的图片）
    document.addEventListener('error', function(e){
        var el = e.target;
        if (el && el.tagName === 'IMG' && !el.dataset.fallbackTried){
            el.dataset.fallbackTried = '1';
            el.src = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22><rect fill=%22%231a2540%22 width=%22400%22 height=%22300%22/><text fill=%22%23566a8a%22 x=%22200%22 y=%22150%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-size=%2248%22>🫧</text></svg>';
        }
    }, true); // 捕获阶段，确保能拦截动态添加的图片

    // 底部导航高亮
    var path = location.pathname;
    document.querySelectorAll('.bottom-nav .tab').forEach(function(t){
        var href = t.getAttribute('href');
        if (href && (path === href || (href !== '/' && path.startsWith(href)))){
            t.classList.add('on');
        }
    });

    // 任务红点
    var dot = document.getElementById('taskDot');
    if (dot && window._hasNewTask) dot.style.display = 'block';

    // 规则弹窗（每次登录后显示一次）
    if (window._currentUserId && window._currentUserId !== null){
        try {
            var shown = sessionStorage.getItem('rules_shown');
            if (!shown) setTimeout(showRules, 800);
        } catch(e) {}
    }

    // 退出时清除弹窗标记，确保下次登录再弹
    var logoutLink = document.querySelector('.logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(){
            try { sessionStorage.removeItem('rules_shown'); } catch(e) {}
        });
    }
});

/* ── 投递（带动画） ───────────────────── */
function doThrow(){
    var form = document.getElementById('throwForm');
    if (!form || !form.checkValidity()){ form.reportValidity(); return; }
    var btn = document.getElementById('throwSubmitBtn');
    if (btn){ btn.disabled = true; btn.textContent = '🌊 投掷中...'; }
    animateThrow(function(){
        setTimeout(function(){ form.submit(); }, 200);
    });
}

/* ── 打捞（带动画） ───────────────────── */
function doSalvage(){
    var btn = document.getElementById('salvageBtn');
    var result = document.getElementById('salvageResult');
    var countEl = document.getElementById('remainingCount');
    if (!btn) return;

    btn.style.pointerEvents = 'none'; btn.style.opacity = '.6';
    var salvageSuccess = false;

    fetch('/api/salvage', {method: 'POST', headers: apiHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(data){
        if (data.success){
            salvageSuccess = true;
            animateSalvage(function(){
                var b = data.bottle;
                var cn = b.category_name || ''; var ci = b.category_icon || '';
                var fh = '';
                if (b.field_a) fh += '<div class="r-field"><span class="r-fl">' + (b.field_a_label || '') + '</span> ' + esc(b.field_a) + '</div>';
                if (b.field_b) fh += '<div class="r-field"><span class="r-fl">' + (b.field_b_label || '') + '</span> ' + esc(b.field_b) + '</div>';
                var rh = b.recommendation ? '<div class="r-rec">💬 ' + esc(b.recommendation) + '</div>' : '';
                if (countEl) countEl.textContent = data.remaining;
                if (data.remaining <= 0){ btn.style.opacity = '.4'; btn.style.pointerEvents = 'none'; }
                if (result){
                    result.innerHTML =
                        '<div class="reveal-card">' +
                        '<img src="/' + b.image_path + '" class="r-img" alt="' + esc(b.title) + '">' +
                        '<div class="r-body">' +
                        '<span class="r-cat">' + ci + ' ' + cn + '</span>' +
                        '<div class="r-title">' + esc(b.title) + '</div>' +
                        '<div class="r-game">🎮 ' + esc(b.game_name) + '</div>' +
                        fh + rh + '</div>' +
                        '<div class="r-actions">' +
                        '<button class="btn-like" onclick="toggleLike(' + b.id + ')"><span class="heart">❤️</span> <span class="lc">' + (b.like_count || 0) + '</span></button>' +
                        '<button class="btn btn-secondary btn-sm" onclick="smartShare(\'bottle\',' + b.id + ',\'' + esc(b.title) + '\')">📤 分享</button>' +
                        '<button class="btn btn-primary btn-sm" onclick="saveToWall(' + b.id + ')">⭐ 收好</button>' +
                        '<a href="/bottle/' + b.id + '" class="btn btn-secondary btn-sm">详情</a>' +
                        '</div></div>';
                    result.classList.remove('hidden');
                    result.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            });
        } else {
            showToast(data.error || '打捞失败', 'error');
        }
    })
    .catch(function(){ showToast('网络错误', 'error'); })
    .finally(function(){
        btn.style.pointerEvents = 'auto'; btn.style.opacity = '';
    });
}

/* ── 点赞 ─────────────────────────────── */
function toggleLike(bid){
    if (!window._currentUserId){ location.href = '/auth/login'; return; }
    var btn = event.target.closest('.btn-like');
    fetch('/api/bottle/' + bid + '/like', {method: 'POST', headers: apiHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success){
            if (d.liked){ btn.classList.add('liked'); }
            else { btn.classList.remove('liked'); }
            var cnt = btn.querySelector('.lc, .like-count, span:last-child');
            if (cnt) cnt.textContent = d.like_count;
        }
    });
}

/* ── 安利墙 ───────────────────────────── */
function saveToWall(id){
    fetch('/api/bottle/' + id + '/save-wall', {method: 'POST', headers: apiHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success) showToast('已加入安利墙！🌟', 'success');
        else showToast(d.error || '收藏失败', 'error');
    })
    .catch(function(){ showToast('网络错误', 'error'); });
}

function removeFromWall(id){
    if (!confirm('从安利墙移除？')) return;
    fetch('/api/bottle/' + id + '/remove-wall', {method: 'POST', headers: apiHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success) location.reload();
        else showToast(d.error || '失败', 'error');
    })
    .catch(function(){ showToast('网络错误', 'error'); });
}

function switchLayout(layout){
    var grid = document.getElementById('wallGrid');
    if (grid){
        grid.classList.remove('nine', 'four');
        grid.classList.add(layout);
    }
}

/* ══════════════════════════════════════════════
   分享图生成（可整体删除，不影响其他功能）
   ══════════════════════════════════════════════ */

var _shareCardQR = null; // QR 实例
var _preRenderedBlob = null; // 预生成的分享图 blob

/* 打开分享图弹窗 → 立即预渲染图片 */
function openShareCard(){
    var overlay = document.getElementById('shareCardOverlay');
    if (!overlay) return;

    // 读取当前布局
    var grid = document.getElementById('wallGrid');
    var layout = (grid && grid.classList.contains('four')) ? 'four' : 'nine';

    // 填充安利墙缩略
    var scWall = document.getElementById('shareCardWall');
    if (scWall){
        scWall.className = 'sc-wall';
        scWall.classList.add(layout === 'four' ? 'four-layout' : 'nine-layout');
        scWall.innerHTML = '';
        var items = document.querySelectorAll('#wallGrid .wall-card img');
        var total = layout === 'four' ? 4 : 9;
        for (var i = 0; i < total; i++){
            if (i < items.length){
                var div = document.createElement('div');
                div.className = 'sc-wall-item';
                var img = document.createElement('img');
                img.src = items[i].src;
                img.alt = '';
                div.appendChild(img);
                scWall.appendChild(div);
            } else {
                var empty = document.createElement('div');
                empty.className = 'sc-wall-empty';
                empty.textContent = '·';
                scWall.appendChild(empty);
            }
        }
    }

    // 生成二维码
    var qrBox = document.getElementById('shareCardQR');
    if (qrBox){
        qrBox.innerHTML = '';
        var refCode = window._referralCode || window._currentUserId || '';
        var qrUrl = location.origin + '/s/wall/' + (window._currentUserId || '') + '?via=' + refCode;
        try {
            _shareCardQR = new QRCode(qrBox, {
                text: qrUrl,
                width: 90,
                height: 90,
                colorDark: '#050d1a',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.M
            });
        } catch(e){
            // 回退：用 API 生成
            var fallback = document.createElement('img');
            fallback.src = 'https://api.qrserver.com/v1/create-qr-code/?size=90x90&data=' + encodeURIComponent(qrUrl);
            fallback.width = 90; fallback.height = 90;
            fallback.alt = 'QR';
            qrBox.appendChild(fallback);
        }
    }

    var inner = document.getElementById('shareCardInner');
    if (inner){
        inner.className = 'sharecard-inner sgbg-theme';
    }

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // 预渲染分享图，确保点击分享时在用户手势上下文中
    _preRenderedBlob = null;
    setTimeout(function(){
        var scInner = document.getElementById('shareCardInner');
        if (!scInner || typeof html2canvas === 'undefined') return;
        html2canvas(scInner, {useCORS:true, allowTaint:false, backgroundColor:null, scale:2})
        .then(function(cvs){
            cvs.toBlob(function(blob){ _preRenderedBlob = blob; }, 'image/png');
        }).catch(function(){});
    }, 400);
}

/* 关闭分享图弹窗 */
function closeShareCard(){
    _preRenderedBlob = null;
    var overlay = document.getElementById('shareCardOverlay');
    if (overlay){
        overlay.style.display = 'none';
    }
    document.body.style.overflow = '';
}


/* 保存分享图 */
function saveShareCard(){
    var inner = document.getElementById('shareCardInner');
    if (!inner) return;

    // 确保所有图片加载完毕
    var imgs = inner.querySelectorAll('img');
    var loaded = 0;
    var total = imgs.length;

    function proceed(){
        if (typeof html2canvas === 'undefined'){
            showToast('html2canvas 加载中，请稍后重试', 'warning');
            return;
        }
        html2canvas(inner, {
            useCORS: true,
            allowTaint: false,
            backgroundColor: null,
            scale: 2  // 2x 清晰度
        }).then(function(canvas){
            // dataURL（base64）：手机浏览器长按保存兼容性好于 blob URL
            var dataUrl = canvas.toDataURL('image/png');
            if (/Mobi|Android|iPhone/i.test(navigator.userAgent)){
                // 移动端：弹图片让用户长按保存（dataURL 可被保存）
                showImageForSave(dataUrl);
            } else {
                // 桌面端：直接下载
                var a = document.createElement('a');
                a.href = dataUrl;
                a.download = '光核安利漂流瓶_分享图.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                showToast('✅ 图片已保存！', 'success');
            }
        }).catch(function(e){
            console.error('html2canvas error:', e);
            showToast('生成失败：' + e.message, 'error');
        });
    }

    if (total === 0){
        proceed();
    } else {
        var timer = setTimeout(function(){ proceed(); }, 3000); // 超时兜底
        imgs.forEach(function(img){
            if (img.complete){
                loaded++;
                if (loaded >= total){ clearTimeout(timer); proceed(); }
            } else {
                img.addEventListener('load', function(){
                    loaded++;
                    if (loaded >= total){ clearTimeout(timer); proceed(); }
                });
                img.addEventListener('error', function(){
                    loaded++;
                    if (loaded >= total){ clearTimeout(timer); proceed(); }
                });
            }
        });
    }
}

/* 移动端显示大图以便长按保存 */
function showImageForSave(dataUrl){
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;';
    overlay.onclick = function(){ overlay.remove(); };

    var img = document.createElement('img');
    img.src = dataUrl;
    img.style.cssText = 'max-width:95vw;max-height:70vh;border-radius:12px;box-shadow:0 0 40px rgba(77,201,246,.3);';

    var tip = document.createElement('p');
    tip.style.cssText = 'color:#e4e8ee;font-size:14px;margin-top:14px;text-align:center;';
    tip.textContent = '👆 长按图片保存到相册';

    var close = document.createElement('button');
    close.textContent = '关闭';
    close.style.cssText = 'margin-top:10px;padding:10px 32px;background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.2);border-radius:20px;font-size:14px;font-weight:600;cursor:pointer;';
    close.onclick = function(e){ e.stopPropagation(); overlay.remove(); };

    // 备选：下载按钮（部分手机浏览器长按 blob/dataURL 仍可能失败）
    var download = document.createElement('button');
    download.textContent = '📥 无法保存？点此下载';
    download.style.cssText = 'margin-top:8px;padding:10px 32px;background:var(--amber,#f78000);color:#fff;border:none;border-radius:20px;font-size:14px;font-weight:600;cursor:pointer;';
    download.onclick = function(e){
        e.stopPropagation();
        var a = document.createElement('a');
        a.href = dataUrl;
        a.download = '光核安利漂流瓶_分享图.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast('✅ 图片已保存！', 'success');
    };

    overlay.appendChild(img);
    overlay.appendChild(tip);
    overlay.appendChild(download);
    overlay.appendChild(close);
    document.body.appendChild(overlay);
}

/* ══ 分享图生成 END ══ */

/* ── 任务 ─────────────────────────────── */
function claimShareReward(){
    fetch('/api/tasks/claim-share', {method: 'POST', headers: apiHeaders()})
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success){ showToast(d.message, 'success'); setTimeout(function(){ location.reload(); }, 1500); }
        else showToast(d.error || '领取失败', 'error');
    })
    .catch(function(){ showToast('网络错误', 'error'); });
}

function trackShare(type, targetId){
    return fetch('/api/share/track', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({type: type, target_id: targetId})
    })
    .then(function(r){ return r.json(); })
    .then(function(d){
        if (d.success && d.share_claimed){
            showToast('✅ 分享成功！获得 +' + d.share_reward + ' 次打捞机会', 'success');
        }
        // 更新剩余次数
        var countEl = document.getElementById('remainingCount');
        if (countEl && d.remaining !== undefined) countEl.textContent = d.remaining;
    });
}

/* ── 智能分享（Web Share API 原生分享 + 剪贴板回退） ── */
function smartShare(type, targetId, title, text){
    var via = window._referralCode || window._currentUserId || '';
    var link = location.origin;
    if (type === 'bottle') link += '/s/bottle/' + targetId + '?via=' + via;
    else if (type === 'wall') link += '/s/wall/' + targetId + '?via=' + via;
    else link += '/?via=' + via;

    var shareTitle = title || '光核安利漂流瓶 🌊';
    var shareText = text || '来光核安利漂流瓶，发现游戏玩家们的宝藏安利！🎮';

    // 优先 Web Share API（手机端拉起 QQ/微信等原生分享面板，桌面端系统分享）
    if (navigator.share) {
        navigator.share({
            title: shareTitle,
            text: shareText,
            url: link
        }).then(function(){
            showToast('✅ 分享成功！好友注册后你能获得拉新奖励～', 'success');
            trackShare(type, targetId);
        }).catch(function(err){
            if (err.name !== 'AbortError'){
                // 分享失败，回退到剪贴板
                fallbackCopyLink(link, type, targetId, '原生分享不可用，已改为复制链接');
            }
        });
    } else {
        // 不支持原生分享（如桌面端 Firefox、HTTP 环境）
        fallbackCopyLink(link, type, targetId);
    }
}

function fallbackCopyLink(link, type, targetId, hint){
    var msg = hint || '📋 链接已复制！好友注册后你能获得拉新奖励～';
    navigator.clipboard.writeText(link).then(function(){
        showToast(msg, 'success');
        trackShare(type, targetId);
    }).catch(function(){
        // 剪贴板也不可用（极少见），弹窗让用户手动复制
        var p = prompt('请手动复制以下链接分享给好友：', link);
        if (p || p === link) trackShare(type, targetId);
    });
}

/* ── 分享链接（兼容旧版调用） ─────────── */
function copyShareLink(type, targetId){
    smartShare(type, targetId);
}

/* 分享图 → 下载回退 */
function fallbackDownload(blob){
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = '光核安利墙.png';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function(){ URL.revokeObjectURL(url); }, 5000);
    showToast('💾 图片已保存到本地！', 'success');
    trackShare('wall', window._currentUserId);
}

/* 分享图 → 链接回退（手机端）或下载（桌面端） */
function shareLinkFallback(blob, link){
    if (/Mobi|Android|iPhone/i.test(navigator.userAgent)){
        // 手机端：复制链接
        navigator.clipboard.writeText(link).then(function(){
            showToast('📋 链接已复制！分享给好友吧～', 'success');
            trackShare('wall', window._currentUserId);
        }).catch(function(){
            fallbackDownload(blob);
        });
    } else {
        fallbackDownload(blob);
    }
}

/* ── 分享图弹窗内：分享图片（预渲染，直接调用原生分享） ── */
function shareCardImage(){
    var shareLink = location.origin + '/s/wall/' + (window._currentUserId || '') + '?via=' + (window._referralCode || window._currentUserId || '');
    var blob = _preRenderedBlob;

    if (!blob){
        showToast('⏳ 图片生成中，请稍后再点～', 'warning');
        var scInner = document.getElementById('shareCardInner');
        if (scInner && typeof html2canvas !== 'undefined'){
            html2canvas(scInner, {useCORS:true, allowTaint:false, backgroundColor:null, scale:2})
            .then(function(cvs){
                cvs.toBlob(function(b){ _preRenderedBlob = b; }, 'image/png');
            }).catch(function(){});
        }
        return;
    }

    if (!navigator.share){
        fallbackDownload(blob);
        return;
    }

    var isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);

    if (isIOS){
        // iOS Safari → 直接分享图片文件（微信能收图片）
        var file = new File([blob], '光核安利墙.png', {type:'image/png'});
        navigator.share({files:[file], title:'光核安利漂流瓶 🌊', text:'来看看我的游戏安利墙！'})
        .then(function(){
            showToast('✅ 分享成功！', 'success');
            trackShare('wall', window._currentUserId);
        }).catch(function(err){
            if (err.name !== 'AbortError') shareLinkFallback(blob, shareLink);
        });
    } else {
        // Android → 分享链接（QQ/微信不支持文件，但链接会展示预览卡片）
        navigator.share({title:'光核安利漂流瓶 🌊', text:'来看看我的游戏安利墙！', url:shareLink})
        .then(function(){
            showToast('✅ 分享成功！', 'success');
            trackShare('wall', window._currentUserId);
        }).catch(function(err){
            if (err.name !== 'AbortError') shareLinkFallback(blob, shareLink);
        });
    }
}

function copyCardLink(){
    var link = location.origin + '/s/wall/' + (window._currentUserId || '') + '?via=' + (window._referralCode || window._currentUserId || '');
    navigator.clipboard.writeText(link).then(function(){
        showToast('✅ 链接已复制！好友注册后你能获得拉新奖励', 'success');
        trackShare('wall', window._currentUserId);
    }).catch(function(){
        prompt('复制以下链接分享给好友：', link);
        trackShare('wall', window._currentUserId);
    });
}
