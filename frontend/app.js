document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');
    
    const approvalGate = document.getElementById('approval-gate');
    const approvalMessage = document.getElementById('approval-message');
    const approvalFeedback = document.getElementById('approval-feedback');
    const btnApprove = document.getElementById('btn-approve');
    const btnReject = document.getElementById('btn-reject');

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle Enter key (Shift+Enter for new line)
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text, 'You');
        userInput.value = '';
        userInput.style.height = 'auto';
        sendBtn.disabled = true;

        try {
            // Call pywebview python function
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.send_message(text);
            } else {
                appendMessage('system', 'Error: pywebview API not found.', 'System');
            }
        } catch (err) {
            appendMessage('system', 'Error connecting to backend: ' + err, 'System');
        } finally {
            sendBtn.disabled = false;
        }
    });

    btnApprove.addEventListener('click', async () => {
        const feedback = approvalFeedback.value.trim();
        approvalGate.classList.add('hidden');
        appendMessage('user', `Approved with feedback: ${feedback}`, 'You (Approval)');
        
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.submit_approval(true, feedback);
            }
        } catch (err) {
            appendMessage('system', 'Error submitting approval: ' + err, 'System');
        }
    });

    btnReject.addEventListener('click', async () => {
        const feedback = approvalFeedback.value.trim();
        approvalGate.classList.add('hidden');
        appendMessage('user', `Rejected/Rerouted with feedback: ${feedback}`, 'You (Rejection)');
        
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.submit_approval(false, feedback);
            }
        } catch (err) {
            appendMessage('system', 'Error submitting rejection: ' + err, 'System');
        }
    });

    function appendMessage(type, text, senderName) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${type}-message`;
        
        let avatarEmoji = '🤖';
        if (type === 'user') avatarEmoji = '👤';
        else if (senderName === 'supervisor') avatarEmoji = '👑';
        else if (senderName === 'coder_agent') avatarEmoji = '💻';
        else if (senderName === 'vision_agent') avatarEmoji = '👁️';
        else if (senderName === 'reasoning_agent') avatarEmoji = '🧠';
        else if (senderName === 'chief_reviewer') avatarEmoji = '🛡️';
        else if (senderName === 'System') avatarEmoji = '⚙️';

        msgDiv.innerHTML = `
            <div class="avatar">${avatarEmoji}</div>
            <div class="bubble">
                ${senderName ? `<div class="agent-name">${senderName}</div>` : ''}
                <div class="content">${escapeHTML(text).replace(/\n/g, '<br>')}</div>
            </div>
        `;
        
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    // Expose functions to Python to call
    window.receiveStreamChunk = function(sender, content) {
        appendMessage('agent', content, sender);
    };

    window.triggerApprovalGate = function(message) {
        approvalMessage.textContent = message;
        approvalFeedback.value = '';
        approvalGate.classList.remove('hidden');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };
});
