// Global State
let currentChatHistory = [];
let messageCount = 0;
let currentQuizAnswer = '';
let currentQuizExplanation = '';

const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const messageCounter = document.getElementById('messageCounter');
const tabButtons = document.querySelectorAll('.tab-btn');
const views = document.querySelectorAll('.view');

function loadSavedChat() {
    const saved = localStorage.getItem('cyber_chat_history');
    const savedCount = localStorage.getItem('cyber_message_count');
    if (saved) {
        try {
            currentChatHistory = JSON.parse(saved);
            messageCount = parseInt(savedCount) || 0;
            messageCounter.textContent = messageCount + ' رسالة';
            chatContainer.innerHTML = '';
            currentChatHistory.forEach(msg => {
                appendMessage(msg.role === 'user' ? 'user' : 'ai', msg.content, false);
            });
        } catch (e) {
            console.error('Failed to load chat history:', e);
        }
    }
}

function saveChat() {
    localStorage.setItem('cyber_chat_history', JSON.stringify(currentChatHistory));
    localStorage.setItem('cyber_message_count', messageCount.toString());
}

tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        tabButtons.forEach(b => b.classList.remove('active'));
        views.forEach(v => v.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(tab + 'View').classList.add('active');
        if(tab === 'news') fetchNews();
        if(tab === 'quiz') fetchQuiz();
    });
});

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    appendMessage('user', message);
    currentChatHistory.push({ role: 'user', content: message });
    saveChat();

    userInput.value = '';
    userInput.style.height = 'auto';

    const thinkingId = showThinkingIndicator();
    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: currentChatHistory })
        });

        let data;
        try {
            data = await response.json();
        } catch (jsonErr) {
            const text = await response.text();
            throw new Error('Server returned invalid JSON: ' + text.substring(0, 200));
        }

        removeThinkingIndicator(thinkingId);

        if (!response.ok) {
            throw new Error(data.detail || 'Server error: ' + response.status);
        }

        const msgType = data.warning ? 'warning' : 'ai';
        appendMessage(msgType, data.response);
        currentChatHistory.push({ role: 'model', content: data.response });
        saveChat();

    } catch (error) {
        removeThinkingIndicator(thinkingId);
        console.error('Chat error:', error);
        appendMessage('error', '❌ خطأ: ' + error.message);
    }

    sendBtn.disabled = false;
    messageCount += 2;
    messageCounter.textContent = messageCount + ' رسالة';
    saveChat();
}

function appendMessage(sender, text, animate) {
    animate = animate !== false;
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender + '-message');
    if (!animate) msgDiv.style.animation = 'none';

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    contentDiv.innerHTML = marked.parse(text);
    contentDiv.querySelectorAll('pre code').forEach(block => {
        hljs.highlightElement(block);
    });

    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showThinkingIndicator() {
    const id = Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', 'ai-message');
    msgDiv.id = 'thinking-' + id;
    msgDiv.innerHTML = '<div class="thinking-indicator"><span></span><span></span><span></span></div>';
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return id;
}

function removeThinkingIndicator(id) {
    const el = document.getElementById('thinking-' + id);
    if(el) el.remove();
}

userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
});

async function fetchNews() {
    const container = document.getElementById('newsContainer');
    container.innerHTML = '<p class="loading-text">جاري جلب أحدث الأخبار...</p>';
    try {
        const res = await fetch('/api/news');
        if (!res.ok) {
            const errText = await res.text();
            throw new Error('HTTP ' + res.status + ': ' + errText.substring(0, 200));
        }
        const news = await res.json();
        container.innerHTML = '';
        if (!Array.isArray(news) || news.length === 0) {
            container.innerHTML = '<p class="error-text">لا توجد أخبار متاحة.</p>';
            return;
        }
        news.forEach(item => {
            container.innerHTML += '<div class="card"><div class="card-category">' + escapeHtml(item.category) + '</div><h3 class="card-title">' + escapeHtml(item.title) + '</h3><p class="card-summary">' + escapeHtml(item.summary) + '</p><small style="color: var(--text-secondary); display: block; margin-top: 10px;">' + escapeHtml(item.date) + '</small></div>';
        });
    } catch(e) {
        console.error('News error:', e);
        container.innerHTML = '<p class="error-text">❌ فشل تحميل الأخبار: ' + escapeHtml(e.message) + '</p>';
    }
}

async function fetchQuiz() {
    const container = document.getElementById('quizContainer');
    container.innerHTML = '<p class="loading-text">جاري إنشاء سؤال جديد...</p>';
    try {
        const res = await fetch('/api/quiz');
        if (!res.ok) {
            const errText = await res.text();
            throw new Error('HTTP ' + res.status + ': ' + errText.substring(0, 200));
        }
        const quiz = await res.json();
        currentQuizAnswer = quiz.correct_answer;
        currentQuizExplanation = quiz.explanation || '';

        let optionsHtml = '';
        quiz.options.forEach(opt => {
            optionsHtml += '<div class="quiz-option" onclick="checkQuizAnswer(this, '' + escapeHtml(opt).replace(/'/g, "\'") + '')">' + escapeHtml(opt) + '</div>';
        });

        container.innerHTML = '<div class="card"><div class="quiz-question">' + escapeHtml(quiz.question) + '</div><div class="quiz-options" id="quizOptions">' + optionsHtml + '</div><div id="quizExplanation" class="quiz-explanation"></div></div>';
    } catch(e) {
        console.error('Quiz error:', e);
        container.innerHTML = '<p class="error-text">❌ فشل تحميل السؤال: ' + escapeHtml(e.message) + '</p>';
    }
}

function checkQuizAnswer(element, selectedAnswer) {
    const options = document.querySelectorAll('.quiz-option');
    options.forEach(opt => opt.classList.add('disabled'));

    const isCorrect = selectedAnswer === currentQuizAnswer;

    if(isCorrect) {
        element.classList.add('correct');
    } else {
        element.classList.add('wrong');
        options.forEach(opt => {
            if(opt.textContent === currentQuizAnswer) opt.classList.add('correct');
        });
    }

    const expDiv = document.getElementById('quizExplanation');
    expDiv.classList.add('show');
    expDiv.innerHTML = '<strong>' + (isCorrect ? '✅ إجابة صحيحة!' : '❌ إجابة خاطئة') + '</strong><br><strong>الإجابة الصحيحة:</strong> ' + escapeHtml(currentQuizAnswer) + '<br>' + (currentQuizExplanation ? '<br><strong>الشرح:</strong> ' + escapeHtml(currentQuizExplanation) : '');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById('newChatBtn').addEventListener('click', () => {
    currentChatHistory = [];
    messageCount = 0;
    messageCounter.textContent = '0 رسالة';
    localStorage.removeItem('cyber_chat_history');
    localStorage.removeItem('cyber_message_count');
    chatContainer.innerHTML = '<div class="message ai-message"><div class="message-content"><p>مرحباً! أنا CyberSentinel AI. كيف يمكنني مساعدتك في مجال الأمن السيبراني اليوم؟</p></div></div>';
});

document.getElementById('refreshNewsBtn').addEventListener('click', fetchNews);
document.getElementById('newQuizBtn').addEventListener('click', fetchQuiz);

document.getElementById('searchInput').addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    const messages = chatContainer.querySelectorAll('.message');
    messages.forEach(msg => {
        const text = msg.textContent.toLowerCase();
        msg.style.display = text.includes(term) ? '' : 'none';
    });
});

const mobileToggle = document.createElement('button');
mobileToggle.className = 'mobile-menu-toggle';
mobileToggle.innerHTML = '☰';
mobileToggle.onclick = () => document.querySelector('.sidebar').classList.toggle('open');
document.body.appendChild(mobileToggle);

// Check backend health on startup
fetch('/api/health')
    .then(r => r.json())
    .then(data => console.log('Backend health:', data))
    .catch(e => console.error('Backend not reachable:', e));

loadSavedChat();
