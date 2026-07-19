// API Configuration - PORT 8001 for MySQL backend
const API_URL = "http://127.0.0.1:8001";

// Read token from URL
const urlParams = new URLSearchParams(window.location.search);
const reviewToken = urlParams.get("token");

console.log("🚀 ReviewShield Frontend Loaded");
console.log("📡 Backend API:", API_URL);
console.log("🔑 Review Token:", reviewToken);

document.addEventListener('DOMContentLoaded', function() {
    
    checkBackendHealth();
    
    // ============ REVIEW SUBMISSION ============
    const submitBtn = document.querySelector('.submit-review');
    
    if (submitBtn) {
        submitBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            
            const name = document.getElementById('customerName')?.value.trim();
            const email = document.getElementById('customerEmail')?.value.trim();
            const review = document.getElementById('reviewText')?.value.trim();
            
            let ratingValue = 0;
            const radioButtons = document.querySelectorAll('input[name="rating"]');
            for (let radio of radioButtons) {
                if (radio.checked) {
                    ratingValue = parseInt(radio.value);
                    break;
                }
            }
            
            // Validation
            if (!name) {
                showNotification('⚠️ Please enter your name!', 'error');
                return;
            }
            if (ratingValue === 0) {
                showNotification('⚠️ Please select a rating!', 'error');
                return;
            }
            if (!email) {
                showNotification('⚠️ Please enter your email!', 'error');
                return;
            }
            if (!email.includes('@')) {
                showNotification('⚠️ Please enter a valid email!', 'error');
                return;
            }
            if (!review) {
                showNotification('⚠️ Please write your review!', 'error');
                return;
            }
            if (review.length < 10) {
                showNotification('⚠️ Review must be at least 10 characters!', 'error');
                return;
            }
            
            // Show loading
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="loading"></span> Submitting...';
            submitBtn.disabled = true;
            
            try {
                // If token exists, use request review endpoint
                let endpoint = `${API_URL}/api/submit-review`;
                let payload = {
                    customer_name: name,
                    email: email,
                    rating: ratingValue,
                    review_text: review
                };
                
                // If reviewToken exists, add to payload
                if (reviewToken) {
                    payload.token = reviewToken;
                }
                
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification(`✅ Review submitted! AI Score: ${result.authenticity_score || result.authenticity || 0}%`, 'success');
                    
                    // Clear form
                    document.getElementById('customerName').value = '';
                    document.getElementById('customerEmail').value = '';
                    document.getElementById('reviewText').value = '';
                    radioButtons.forEach(radio => radio.checked = false);
                    
                    updateReviewStats();
                } else {
                    showNotification(`❌ Error: ${result.detail || result.message || 'Submission failed'}`, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('❌ Cannot connect to backend. Make sure server is running on port 8001', 'error');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }
    
    // ============ AUTO REVIEW REQUEST ============
    const sendRequestBtn = document.getElementById('sendRequestBtn');
    if (sendRequestBtn) {
        sendRequestBtn.addEventListener('click', async function() {
            const email = document.getElementById('autoEmail')?.value.trim();
            const name = document.getElementById('autoName')?.value.trim();
            const product = document.getElementById('autoProduct')?.value.trim();
            
            if (!email || !name) {
                showNotification('⚠️ Please enter customer email and name!', 'error');
                return;
            }
            
            sendRequestBtn.innerHTML = 'Sending...';
            sendRequestBtn.disabled = true;
            
            try {
                const response = await fetch(`${API_URL}/api/review-requests/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        customer_name: name,
                        customer_email: email,
                        order_id: 'AUTO-' + Date.now(),
                        product_name: product || 'Product'
                    })
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    const statusDiv = document.getElementById('requestStatus');
                    statusDiv.innerHTML = `
                        <div style="background:#10b981; color:white; padding:12px; border-radius:8px; margin-top:15px;">
                            ✅ Request created! 
                            <a href="${result.review_link}" target="_blank" style="color:white; text-decoration:underline;">
                                ${result.review_link}
                            </a>
                            <button onclick="copyToClipboard('${result.review_link}')" style="background:white; color:#10b981; border:none; padding:4px 12px; border-radius:4px; cursor:pointer; margin-left:10px;">
                                📋 Copy
                            </button>
                        </div>
                    `;
                    showNotification('✅ Review request created!', 'success');
                    
                    document.getElementById('autoEmail').value = '';
                    document.getElementById('autoName').value = '';
                    document.getElementById('autoProduct').value = '';
                } else {
                    showNotification(`❌ Failed to create request: ${result.error || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('❌ Cannot connect to server', 'error');
            } finally {
                sendRequestBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Request';
                sendRequestBtn.disabled = false;
            }
        });
    }
    
    // ============ REVIEW STATS ============
    async function updateReviewStats() {
        try {
            const response = await fetch(`${API_URL}/api/stats`);
            if (!response.ok) return;
            const stats = await response.json();
            
            let statsDiv = document.querySelector('.review-stats');
            if (!statsDiv) {
                statsDiv = document.createElement('div');
                statsDiv.className = 'review-stats';
                statsDiv.style.cssText = `position:fixed; bottom:20px; left:20px; background:white; padding:12px 24px; border-radius:50px; box-shadow:0 4px 15px rgba(0,0,0,0.1); font-size:14px; z-index:99; cursor:pointer; font-weight:500;`;
                statsDiv.onclick = () => showAllReviews();
                document.body.appendChild(statsDiv);
            }
            statsDiv.innerHTML = `📊 ${stats.verified_reviews || 0} Verified | 🤖 ${stats.spam_reviews || 0} Flagged | ⭐ ${stats.average_rating || 0}`;
        } catch (error) {
            console.log('Stats not available');
        }
    }
    
    // ============ SHOW ALL REVIEWS ============
    window.showAllReviews = async function() {
        try {
            const response = await fetch(`${API_URL}/api/reviews?limit=50`);
            if (!response.ok) throw new Error('Failed');
            const reviews = await response.json();
            
            if (reviews.length === 0) {
                showNotification('📭 No reviews yet!', 'info');
                return;
            }
            
            let modal = document.querySelector('.reviews-modal');
            if (modal) modal.remove();
            
            modal = document.createElement('div');
            modal.style.cssText = `position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); display:flex; justify-content:center; align-items:center; z-index:1000;`;
            
            modal.innerHTML = `
                <div style="background:white; border-radius:24px; max-width:700px; width:90%; max-height:80%; overflow:auto; padding:30px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
                        <h2>📋 All Reviews</h2>
                        <button onclick="this.closest('.reviews-modal').remove()" style="background:none; border:none; font-size:28px; cursor:pointer;">&times;</button>
                    </div>
                    ${reviews.map(r => `
                        <div style="border-bottom:1px solid #e2e8f0; padding:15px 0;">
                            <div style="display:flex; justify-content:space-between;">
                                <strong>${escapeHtml(r.customer_name)}</strong>
                                <span style="color:${r.is_spam ? '#ef4444' : '#10b981'}">${r.is_spam ? '⚠️ Flagged' : '✅ Verified'} | ${r.authenticity_score || 0}%</span>
                            </div>
                            <div style="color:#f59e0b;">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</div>
                            <p>${escapeHtml(r.review_text)}</p>
                            <small>${new Date(r.created_at).toLocaleString()}</small>
                        </div>
                    `).join('')}
                </div>
            `;
            modal.className = "reviews-modal";
            document.body.appendChild(modal);
            
            // Close on outside click
            modal.addEventListener('click', function(e) {
                if (e.target === modal) modal.remove();
            });
            
        } catch (error) {
            console.error('Error:', error);
            showNotification('Cannot fetch reviews!', 'error');
        }
    };
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ============ COPY TO CLIPBOARD ============
    window.copyToClipboard = async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            showNotification('✅ Link copied to clipboard!', 'success');
        } catch (err) {
            // Fallback
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showNotification('✅ Link copied!', 'success');
        }
    };
    
    // ============ NAVIGATION ============
    document.querySelectorAll('.navbar li').forEach(item => {
        const text = item.textContent.trim();
        item.addEventListener('click', () => {
            if (text === 'Reviews') showAllReviews();
            else if (text === 'Home') window.scrollTo({ top: 0, behavior: 'smooth' });
            else if (text === 'How it Works') showModal('How It Works', '1. Submit Review → 2. AI Analysis → 3. Verified/Flagged');
            else if (text === 'Contact') showModal('Contact', '📧 support@reviewshield.com');
            else if (text === 'About') showModal('About', 'AI-Powered Review Management System');
        });
    });
    
    document.querySelector('.submit-btn')?.addEventListener('click', () => {
        document.querySelector('.experience')?.scrollIntoView({ behavior: 'smooth' });
    });
    
    document.querySelector('.learn-btn')?.addEventListener('click', () => {
        showModal('Why ReviewShield?', 'AI-powered spam detection with 95% accuracy!');
    });
    
    // ============ NOTIFICATION ============
    function showNotification(message, type) {
        const existing = document.querySelector('.notification-toast');
        if (existing) existing.remove();
        
        const notif = document.createElement('div');
        const colors = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', info: '#2563eb' };
        notif.style.cssText = `position:fixed; bottom:30px; right:30px; padding:14px 24px; background:${colors[type] || colors.info}; color:white; border-radius:16px; z-index:1001; animation:slideIn 0.3s ease; box-shadow:0 10px 25px rgba(0,0,0,0.1);`;
        notif.textContent = message;
        document.body.appendChild(notif);
        setTimeout(() => {
            notif.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notif.remove(), 300);
        }, 4000);
    }
    
    // ============ MODAL ============
    function showModal(title, content) {
        let modal = document.querySelector('.info-modal');
        if (modal) modal.remove();
        modal = document.createElement('div');
        modal.className = "info-modal";
        modal.style.cssText = `position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); display:flex; justify-content:center; align-items:center; z-index:1000;`;
        modal.innerHTML = `
            <div style="background:white; border-radius:24px; max-width:400px; width:90%; padding:30px;">
                <h2>${title}</h2>
                <p style="margin-top:15px;">${content}</p>
                <button onclick="this.closest('.info-modal').remove()" style="margin-top:20px; background:#2563eb; color:white; border:none; padding:10px 20px; border-radius:12px; cursor:pointer;">Close</button>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close on outside click
        modal.addEventListener('click', function(e) {
            if (e.target === modal) modal.remove();
        });
        
        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal) modal.remove();
        });
    }
    
    // ============ CHECK BACKEND ============
    async function checkBackendHealth() {
        try {
            const response = await fetch(`${API_URL}/api/health`);
            if (response.ok) {
                console.log('✅ Backend connected on port 8001');
                showNotification('✅ Connected to ReviewShield Server', 'success');
                updateReviewStats();
            } else {
                console.warn('⚠️ Backend responded but with error');
            }
        } catch (error) {
            console.warn('⚠️ Backend not running on port 8001');
            showNotification('⚠️ Backend not running. Start: python main_mysql.py', 'warning');
        }
    }
    
    // ============ ADD CSS ============
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn{from{transform:translateX(100%);opacity:0;}to{transform:translateX(0);opacity:1;}}
        @keyframes slideOut{from{transform:translateX(0);opacity:1;}to{transform:translateX(100%);opacity:0;}}
        .loading{display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,0.3);border-radius:50%;border-top-color:white;animation:spin 0.6s linear infinite;margin-right:8px;}
        @keyframes spin{to{transform:rotate(360deg);}}
    `;
    document.head.appendChild(style);
    
    console.log('✅ ReviewShield Frontend Ready!');
});