document.addEventListener("DOMContentLoaded", () => {
    // ... (todo tu código anterior de animaciones, calculadora ROI, etc.) ...

    // =========================================
    // WIDGET CHAT ASESOR IA (CORREGIDO)
    // =========================================
    document.addEventListener('DOMContentLoaded', function() {
        const toggleBtn = document.getElementById('toggle-chat-btn');
        const closeBtn = document.getElementById('close-chat-btn');
        const chatWindow = document.getElementById('ai-chat-window');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');
        const chatMessages = document.getElementById('chat-messages');
        let chatHistory = [];
        let isOpen = false;

        if (toggleBtn && chatWindow) {
            toggleBtn.addEventListener('click', function(e) {
                e.preventDefault();
                isOpen = !isOpen;
                chatWindow.style.display = isOpen ? 'flex' : 'none';
                if (isOpen && chatInput) setTimeout(() => chatInput.focus(), 100);
            });

            if (closeBtn) {
                closeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    isOpen = false;
                    chatWindow.style.display = 'none';
                });
            }

            document.addEventListener('click', function(e) {
                if (isOpen && !chatWindow.contains(e.target) && !toggleBtn.contains(e.target)) {
                    isOpen = false;
                    chatWindow.style.display = 'none';
                }
            });
        }

        if (chatForm && chatInput) {
            chatForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                const message = chatInput.value.trim();
                if (!message) return;

                const userMsg = document.createElement('div');
                userMsg.className = 'msg-user';
                userMsg.textContent = message;
                chatMessages.appendChild(userMsg);
                chatInput.value = '';
                chatMessages.scrollTop = chatMessages.scrollHeight;

                const loader = document.createElement('div');
                loader.className = 'msg-loading';
                loader.textContent = ' Analizando...';
                chatMessages.appendChild(loader);
                chatMessages.scrollTop = chatMessages.scrollHeight;

                try {
                    const res = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message, history: chatHistory })
                    });
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    const data = await res.json();
                    loader.remove();

                    const botMsg = document.createElement('div');
                    botMsg.className = 'msg-bot';
                    
                    let responseText = data.response || 'Lo siento, no pude procesar tu mensaje.';

                    // 🔥 CORRECCIÓN CRÍTICA: Generación Automática de Link WhatsApp Seguro
                    const phoneRegex = /(\+?\d{7,15})/; 
                    const userPhoneMatch = message.match(phoneRegex);

                    if (userPhoneMatch || (responseText.toLowerCase().includes('agendar') && responseText.toLowerCase().includes('whatsapp'))) {
                        let cleanPhone = "";
                        
                        if (userPhoneMatch) {
                            cleanPhone = userPhoneMatch[0].replace(/\D/g, '');
                        } else {
                            const lastUserMsg = [...chatHistory].reverse().find(m => m.role === 'user');
                            if (lastUserMsg) {
                                const histMatch = lastUserMsg.content.match(phoneRegex);
                                if (histMatch) cleanPhone = histMatch[0].replace(/\D/g, '');
                            }
                        }

                        if (cleanPhone.length >= 7) {
                            if (!cleanPhone.startsWith('57')) {
                                cleanPhone = '57' + cleanPhone;
                            }
                            
                            const whatsappLink = `https://wa.me/${cleanPhone}?text=${encodeURIComponent('Hola, confirmo mi interés.')}`;
                            responseText += `<br><br>👉 <a href="${whatsappLink}" target="_blank" style="display: inline-block; background-color: #25D366; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: bold;"> Abrir WhatsApp</a>`;
                        }
                    }

                    botMsg.innerHTML = responseText;
                    chatMessages.appendChild(botMsg);

                    chatHistory.push({ role: 'user', content: message });
                    chatHistory.push({ role: 'assistant', content: data.response });
                    chatMessages.scrollTop = chatMessages.scrollHeight;

                } catch (error) {
                    console.error(error);
                    loader.remove();
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'msg-error';
                    errorMsg.textContent = '⚠️ Error de conexión.';
                    chatMessages.appendChild(errorMsg);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            });
        }
    });
});
