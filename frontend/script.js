// script.js

const MAX_CHARS = 100;
let isLoggedIn = false;
let currentUser = null;
let isSubscribed = true;
let subscriptionEndDate = null;

// Stripe-related variables
let stripe;
let elements;
let card;

// Function to get users from local storage
function getUsers() {
    const users = localStorage.getItem('users');
    return users ? JSON.parse(users) : [];
}

// Function to save users to local storage
function saveUsers(users) {
    localStorage.setItem('users', JSON.stringify(users));
}

// Function to update the console output
function updateConsole(message, color = 'white') {
    const consoleOutput = document.getElementById('console-output');
    consoleOutput.innerHTML += `<span style="color: ${color};">${message}</span>\n`;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// Function to create a message element for chat display
function createMessageElement(text, type) {
    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}-message`;

    const chunks = text.match(new RegExp(`.{1,${MAX_CHARS}}`, 'g')) || [];
    chunks.forEach(chunk => {
        const line = document.createElement('pre');
        line.textContent = chunk;
        line.style.margin = '2px 0';
        line.style.padding = '5px';
        line.style.overflowWrap = 'break-word';
        line.style.whiteSpace = 'pre-wrap';
        messageElement.appendChild(line);
    });

    return messageElement;
}

// Function to send a message to the backend
function sendMessage() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const userInput = document.getElementById('user-input').value;
    if (userInput) {
        updateConsole(`User: ${userInput}`, 'green');

        // Display "Open Quantum AI is Coding" in both console and chat
        updateConsole("Open Quantum AI is Coding", 'blue');
        const messageDisplay = document.getElementById('message-display');
        messageDisplay.appendChild(createMessageElement("Open Quantum AI is Coding", 'bot'));

        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userInput })
        })
        .then(response => response.json())
        .then(data => {
            if (data.console) {
                updateConsole(data.console, 'cyan');
            }

            messageDisplay.appendChild(createMessageElement(`User: ${userInput}`, 'user'));

            if (data.response) {
                messageDisplay.appendChild(createMessageElement(`OQ-AI: ${data.response}`, 'bot'));
                updateConsole(`OQ-AI: ${data.response}`, 'blue');
            }

            document.getElementById('user-input').value = '';
            messageDisplay.scrollTop = messageDisplay.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            updateConsole(`Error sending message: ${error.message}`, 'red');
        });
    }
}

// Event listeners for sending messages
document.getElementById('send').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        if (isSubscribed) {
            sendMessage();
        } else {
            updateConsole("You need a subscription to use this feature.", 'red');
        }
        event.preventDefault();
    }
});

// Function to connect the API key
function connectApiKey() {
    const apiKey = document.getElementById('api-key').value;
    if (apiKey) {
        fetch('/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apiKey: apiKey })
        })
        .then(response => response.json())
        .then(data => {
            console.log('API Key connected:', data);
            updateConsole('API Key connected successfully', 'purple');
        })
        .catch(error => {
            console.error('Error:', error);
            updateConsole(`Error connecting API Key: ${error.message}`, 'red');
        });
    }
}

// usersystem interval functionality
let usersystemInterval;

document.getElementById('set-timer').addEventListener('click', function() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const seconds = parseInt(document.getElementById('timer-input').value);
    
    clearInterval(usersystemInterval);
    
    if (seconds > 0) {
        usersystemInterval = setInterval(() => {
            fetch('/check-usersystem', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: "(DATA FETCHING TIMER ACTIVATED) Check usersystem status and token prices for potential buy/sell opportunities." })
            })
            .then(response => response.json())
            .then(data => {
                updateConsole(`usersystem Check: ${data.response}`, 'purple');
            });

            fetch('/fetch-ai-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: "(DATA FETCHING TIMER ACTIVATED).Check usersystem status and token prices for potential buy/sell opportunities" })
            })
            .then(response => response.json())
            .then(data => {
                updateConsole(`AI Data Fetch: ${data.response}`, 'purple');
            })
            .catch(error => {
                console.error('Error:', error);
                updateConsole(`Error fetching data from AI: ${error.message}`, 'red');
            });
        }, seconds * 1000);

        updateConsole(`Timer set to check usersystem and fetch AI data every ${seconds} seconds.`, 'green');
    } else {
        updateConsole('Timer cleared. usersystem checks and AI data fetching stopped.', 'orange');
    }
});

// Popup management functions
function showPopup(popupId) {
    document.querySelectorAll('.popup').forEach(popup => popup.style.display = 'none');
    document.getElementById(popupId).style.display = 'block';
}

function closePopup(popupId) {
    document.getElementById(popupId).style.display = 'none';
}

// User authentication functions
function signup() {
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('signup-confirm-password').value;
    
    if (password !== confirmPassword) {
        alert("Passwords do not match!");
        return;
    }
    
    // For demonstration, we're sending an email using SMTP.js (you should configure this properly)
    Email.send({
        Host: "smtp.elasticemail.com",
        Port: "2525",
        Username: "your-email@example.com",
        Password: "your-email-password",
        To: 'your-notification-email@example.com',
        From: "your-email@example.com",
        Subject: "New User Signup",
        Body: `A new user has signed up with email: ${email}`
    }).then(
        message => {
            alert("Signup successful! Email sent.");
            closePopup('signup-popup');
            login(email, password);
        }
    ).catch(
        error => {
            console.error("Error sending email:", error);
            alert("Signup successful, but there was an error sending the notification email.");
        }
    );
}

function login(email = null, password = null) {
    if (!email || !password) {
        email = document.getElementById('login-email').value;
        password = document.getElementById('login-password').value;
    }
    
    // Here you would typically validate with your server
    console.log("Login:", { email, password });
    isLoggedIn = true;
    currentUser = email;
    updateLoginState();
    closePopup('login-popup');
}

function logout() {
    isLoggedIn = false;
    currentUser = null;
    isSubscribed = false;
    subscriptionEndDate = null;
    updateLoginState();
}

function recoverAccount() {
    const email = document.getElementById('recover-email').value;
    
    // Here you would typically send this to your server
    console.log("Recover account for:", email);
    closePopup('recover-popup');
}

function resetPassword() {
    const newPassword = document.getElementById('new-password').value;
    const confirmNewPassword = document.getElementById('confirm-new-password').value;
    
    if (newPassword !== confirmNewPassword) {
        alert("Passwords do not match!");
        return;
    }
    
    // Here you would typically send this to your server
    console.log("Reset password");
    closePopup('reset-password-popup');
}

function updateLoginState() {
    const apiKeyInput = document.getElementById('api-key');
    const connectButton = document.getElementById('connect');
    const signupBtn = document.getElementById('signup-btn');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const subscribeBtn = document.getElementById('subscribe-btn');

    if (isLoggedIn) {
        apiKeyInput.disabled = false;
        connectButton.disabled = false;
        signupBtn.style.display = 'none';
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'inline-block';
        subscribeBtn.style.display = 'inline-block';
        updateSubscriptionStatus();
    } else {
        apiKeyInput.disabled = true;
        connectButton.disabled = true;
        signupBtn.style.display = 'inline-block';
        loginBtn.style.display = 'inline-block';
        logoutBtn.style.display = 'none';
        subscribeBtn.style.display = 'none';
        lockFeatures();
    }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
    updateLoginState();
    initializeStripe();
});

// Function to update system prompt with user instructions
function updateSystemPrompt() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const userInstruction = document.getElementById('user-instruction').value.trim();
    if (userInstruction) {
        fetch('/update-instructions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction: userInstruction })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'updated') {
                updateConsole('System prompt updated with user instructions.', 'purple');
                document.getElementById('user-instruction').value = '';
            } else {
                updateConsole('Failed to update system prompt.', 'red');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            updateConsole(`Error updating instructions: ${error.message}`, 'red');
        });
    } else {
        alert("Please enter an instruction before updating.");
    }
}

document.getElementById('send-instruction').addEventListener('click', updateSystemPrompt);

// Function to clear conversation
function clearConversation() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    // Clear the message display in the frontend
    const messageDisplay = document.getElementById('message-display');
    messageDisplay.innerHTML = '<button id="clear-conversation" class="clear-btn">X Clear Conversation</button>';
    // Re-attach the event listener
    document.getElementById('clear-conversation').addEventListener('click', clearConversation);

    // Clear the conversation on the backend
    fetch('/clear-conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'cleared') {
            updateConsole('Conversation history cleared.', 'orange');
        } else {
            updateConsole('Failed to clear conversation history.', 'red');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        updateConsole(`Error clearing conversation: ${error.message}`, 'red');
    });
}

// Re-attach the event listener for the clear conversation button
document.getElementById('clear-conversation').addEventListener('click', clearConversation);

// Initialize SSE for streaming logs
function initializeLogStream() {
    const eventSource = new EventSource('/stream-logs');

    eventSource.onmessage = function(event) {
        const message = event.data;
        // You can parse the message if it's in a specific format
        updateConsole(message, 'grey');
    };

    eventSource.onerror = function(err) {
        console.error("EventSource failed:", err);
        updateConsole('Log stream connection lost.', 'red');
        eventSource.close();
    };
}

// Call this function when the page loads
window.onload = function() {
    initializeLogStream();
};

// Quantum SHA256 Functionality
let sha256Mode = 'store';

function setSha256Mode(mode) {
    sha256Mode = mode;
    document.getElementById('sha256-store-section').style.display = mode === 'store' ? 'block' : 'none';
    document.getElementById('sha256-verify-section').style.display = mode === 'verify' ? 'block' : 'none';
}

function storeSignature() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const textInput = document.getElementById('sha256-input').value;
    const fileInput = document.getElementById('sha256-file-input').files[0];
    const tag = document.getElementById('sha256-tag').value.trim();

    if (!tag) {
        alert('Please enter a tag name.');
        return;
    }

    let content = textInput;

    if (fileInput) {
        const reader = new FileReader();
        reader.onload = function(e) {
            content = e.target.result;
            processSha256Signature(content, tag, 'store');
        };
        reader.readAsText(fileInput);
    } else {
        processSha256Signature(content, tag, 'store');
    }
}

function verifySha256Signature() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const textInput = document.getElementById('sha256-input-verify').value;
    const fileInput = document.getElementById('sha256-file-input-verify').files[0];
    const tag = document.getElementById('sha256-verify-tag').value.trim();

    if (!tag) {
        alert('Please enter a tag name.');
        return;
    }

    let content = textInput;

    if (fileInput) {
        const reader = new FileReader();
        reader.onload = function(e) {
            content = e.target.result;
            processSha256Signature(content, tag, 'verify');
        };
        reader.readAsText(fileInput);
    } else {
        processSha256Signature(content, tag, 'verify');
    }
}

function processSha256Signature(content, tag, action) {
    fetch(`/quantum-sha256-${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, tag })
    })
    .then(response => response.json())
    .then(data => {
        if (action === 'store') {
            alert('Signature stored successfully.');
            closePopup('quantum-sha256-popup');
        } else if (action === 'verify') {
            const qubitsOutput = document.getElementById('sha256-qubits-output');
            qubitsOutput.textContent = `Qubits Output: ${data.message}`;
            if (data.match) {
                alert('Signatures match! Verification successful.');
            } else {
                alert('Signatures do not match. Verification failed.');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while processing the signature.');
    });
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    element.select();
    document.execCommand('copy');
    alert('Copied to clipboard!');
}
// Quantum RSA Functionality
function generateKeyPair() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    fetch('/quantum-rsa-generate', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('rsa-keypair-output').textContent = `Public Key: ${data.publicKey}\nPrivate Key: ${data.privateKey}`;
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while generating the key pair.');
    });
}

function encryptMessage() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const publicKey = document.getElementById('rsa-public-key').value;
    const message = document.getElementById('rsa-encrypt-input').value;

    fetch('/quantum-rsa-encrypt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ publicKey, message })
    })
    .then(response => response.json())
    .then(data => {
        const encryptionResult = document.getElementById('encryption-result');
        encryptionResult.value = `Encrypted Message: ${data.encryptedMessage}`;
        encryptionResult.style.display = 'block';
        alert('Encryption successful!');
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while encrypting the message.');
    });
}

function decryptMessage() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const privateKey = document.getElementById('rsa-private-key').value;
    const message = document.getElementById('rsa-decrypt-input').value;

    fetch('/quantum-rsa-decrypt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ privateKey, message })
    })
    .then(response => response.json())
    .then(data => {
        const decryptionResult = document.getElementById('decryption-result');
        decryptionResult.value = `Decrypted Message: ${data.decryptedMessage}`;
        decryptionResult.style.display = 'block';
        alert('Decryption successful!');
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while decrypting the message.');
    });
}

// Search and Verify Signature
function searchTag() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const tag = document.getElementById('search-tag').value.trim();

    if (!tag) {
        alert('Please enter a tag to search.');
        return;
    }

    fetch('/quantum-sha256-verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag })
    })
    .then(response => response.json())
    .then(data => {
        if (data.signature) {
            document.getElementById('verification-result').innerHTML = `Stored Signature (HEX): <br>${data.signature}`;
        } else {
            document.getElementById('verification-result').textContent = 'Tag not found.';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while searching for the tag.');
    });
}

function verifySignature() {
    if (!isSubscribed) {
        updateConsole("You need a subscription to use this feature.", 'red');
        return;
    }

    const inputSignature = document.getElementById('input-signature').value;
    const storedSignature = document.getElementById('verification-result').textContent.split(': ')[1];

    if (!inputSignature || !storedSignature) {
        alert('Please search for a tag and enter a signature to verify.');
        return;
    }

    const inputHex = inputSignature.toLowerCase().replace(/[^0-9a-f]/g, '');
    const storedHex = storedSignature.toLowerCase().replace(/[^0-9a-f]/g, '');

    if (inputHex === storedHex) {
        document.getElementById('verification-result').innerHTML += '<br><span style="color: green;">Signatures match!</span>';
    } else {
        document.getElementById('verification-result').innerHTML += '<br><span style="color: red;">Signatures do not match.</span>';
    }
}

// Stripe Integration
function initializeStripe() {
    stripe = Stripe('pk_live_51PzV2GF79vOiQLEKpFRksn9EY9u9zEII4HW9SiNh0u1hjbJuMZG2KJEuXG5YFsNouC4whiAQcR80KUVTzMvIvd9V00iHfILaEZ');
    elements = stripe.elements();
    card = elements.create('card');
    card.mount('#card-element');

    card.addEventListener('change', function(event) {
        var displayError = document.getElementById('card-errors');
        if (event.error) {
            displayError.textContent = event.error.message;
        } else {
            displayError.textContent = '';
        }
    });

    var form = document.getElementById('subscribe-popup');
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        createSubscription();
    });
}

function createSubscription() {
    stripe.createPaymentMethod({
        type: 'card',
        card: card,
    }).then(function(result) {
        if (result.error) {
            var errorElement = document.getElementById('card-errors');
            errorElement.textContent = result.error.message;
        } else {
            fetch('/create-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    payment_method: result.paymentMethod.id,
                    email: currentUser,
                }),
            }).then(function(response) {
                return response.json();
            }).then(function(subscription) {
                if (subscription.status === 'active') {
                    isSubscribed = true;
                    subscriptionEndDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000); // 30 days from now
                    updateSubscriptionStatus();
                    closePopup('subscribe-popup');
                    alert('Subscription successful!');
                } else {
                    alert('Subscription failed. Please try again.');
                }
            });
        }
    });
}

function updateSubscriptionStatus() {
    if (isSubscribed && subscriptionEndDate > new Date()) {
        unlockFeatures();
    } else {
        lockFeatures();
    }
}

// Event listeners for the new functionality
document.getElementById('quantum-sha256-btn').addEventListener('click', () => {
    if (isSubscribed) {
        showPopup('quantum-sha256-popup');
    } else {
        updateConsole("You need a subscription to use this feature.", 'red');
    }
});
document.getElementById('quantum-rsa-btn').addEventListener('click', () => {
    if (isSubscribed) {
        showPopup('quantum-rsa-popup');
    } else {
        updateConsole("You need a subscription to use this feature.", 'red');
    }
});
document.getElementById('search-tag-btn').addEventListener('click', searchTag);
document.getElementById('verify-signature-btn').addEventListener('click', verifySignature);
document.getElementById('stripe-button').addEventListener('click', createSubscription);

// Close buttons for popups
function addCloseButton(popupId) {
    const closeButton = document.createElement('button');
    closeButton.textContent = 'Close';
    closeButton.onclick = function() {
        closePopup(popupId);
    };
    return closeButton;
}

// Adding close buttons for login and signup popups
const signupPopup = document.getElementById('signup-popup');
const loginPopup = document.getElementById('login-popup');

signupPopup.appendChild(addCloseButton('signup-popup'));
loginPopup.appendChild(addCloseButton('login-popup'));
