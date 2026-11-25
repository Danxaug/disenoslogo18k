document.addEventListener("DOMContentLoaded", () => {
    // Animaciones AOS
    if (window.AOS) AOS.init({ duration: 800, once: true, easing: "ease-out-cubic" });

    // Formulario de Pedido
    const form = document.getElementById("pedidoForm");
    
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById("submitBtn");
            const formStatus = document.getElementById("formStatus");
            
            const fd = new FormData(form);
            const nombre = fd.get("nombre");
            const telefono = fd.get("telefono");
            const interes = fd.get("interes");

            if(submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<span>Procesando...</span>`;
            }
            if(formStatus) formStatus.textContent = "";

            // Número de WhatsApp de la empresa
            const YOUR_PHONE = "573174827958"; 
            const msg = encodeURIComponent(`Hola Diseños Logo, soy ${nombre}. Quiero agendar cita VIP. Mi teléfono es ${telefono} y me interesa: ${interes}.`);
            const directWhatsAppLink = `https://wa.me/${YOUR_PHONE}?text=${msg}`;

            try {
                const res = await fetch("/procesar_pedido", { 
                    method: "POST", 
                    headers: { "Content-Type": "application/x-www-form-urlencoded" }, 
                    body: new URLSearchParams({ nombre, telefono, interes })
                });

                if (res.ok) {
                    const redirectUrl = res.url;
                    if (redirectUrl && redirectUrl.includes("wa.me")) {
                        window.location.href = redirectUrl;
                        return;
                    }
                }
                
                throw new Error("Backend no respondió correctamente.");

            } catch (err) {
                console.warn("Fallback a WhatsApp directo:", err);
                
                if(formStatus) formStatus.textContent = "Conectando con WhatsApp...";
                
                setTimeout(() => {
                     window.open(directWhatsAppLink, '_blank');
                     
                     if(submitBtn) {
                         submitBtn.disabled = false;
                         submitBtn.innerHTML = `<span>Enviar</span>`;
                     }
                }, 800);
            }
        });
    }

    // Widget Chat IA
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

                // 🔥 CORRECCIÓN: Generación automática de botón WhatsApp
                const phoneRegex = /(\+?\d{7,15})/; 
                const userPhoneMatch = message.match(phoneRegex);

                if (userPhoneMatch || (responseText.toLowerCase().includes('whatsapp') && responseText.toLowerCase().includes('clic'))) {
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
                        
                        const whatsappLink = `https://wa.me/${cleanPhone}?text=${encodeURIComponent('Hola Diseños Logo, confirmo mi interés en agendar cita VIP.')}`;
                        responseText += `<br><br>👉 <a href="${whatsappLink}" target="_blank" style="display: inline-block; background-color: #F59E0B; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; font-family: sans-serif; margin-top: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);"> Confirmar Cita por WhatsApp</a>`;
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
                errorMsg.textContent = '⚠️ Error de conexión. Escríbenos directo al WhatsApp.';
                chatMessages.appendChild(errorMsg);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        });
    }
});