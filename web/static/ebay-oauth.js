/**
 * eBay OAuth Manager for Callback URL Flow
 * Handles eBay authentication using configured callback URLs
 */
class EbayOAuthManager {
    constructor() {
        this.popup = null;
        this.checkInterval = null;
        this.messageListener = null;
        this.authState = null;
    }

    /**
     * Start the OAuth flow by opening a popup window
     */
    async startOAuthFlow(options = {}) {
        const { onSuccess, onError, onCancel } = options;

        try {
            // Get OAuth URL from backend
            const response = await fetch('/api/ebay-oauth-url');
            if (!response.ok) {
                throw new Error(`Failed to get OAuth URL: ${response.statusText}`);
            }
            
            const data = await response.json();
            const { auth_url, state } = data;
            this.authState = state;

            console.log('Starting eBay OAuth flow with URL:', auth_url);

            // Open popup window
            this.openPopup(auth_url, {
                onSuccess: async (authData) => {
                    try {
                        // Exchange code for tokens
                        const tokenResponse = await fetch('/api/ebay-exchange-token', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                code: authData.code,
                                state: authData.state
                            })
                        });

                        if (!tokenResponse.ok) {
                            const errorData = await tokenResponse.json();
                            throw new Error(errorData.error || 'Token exchange failed');
                        }

                        const tokenData = await tokenResponse.json();
                        
                        if (onSuccess) {
                            onSuccess(tokenData);
                        }
                    } catch (error) {
                        if (onError) {
                            onError(error);
                        }
                    }
                },
                onError: (error) => {
                    if (onError) {
                        onError(new Error(error));
                    }
                },
                onCancel: () => {
                    if (onCancel) {
                        onCancel();
                    }
                }
            });

        } catch (error) {
            if (onError) {
                onError(error);
            }
        }
    }

    /**
     * Open popup window and handle communication
     */
    openPopup(url, callbacks) {
        const { onSuccess, onError, onCancel } = callbacks;

        // Popup window settings
        const popupWidth = 600;
        const popupHeight = 700;
        const left = (window.screen.width - popupWidth) / 2;
        const top = (window.screen.height - popupHeight) / 2;

        const popupFeatures = [
            `width=${popupWidth}`,
            `height=${popupHeight}`,
            `left=${left}`,
            `top=${top}`,
            'scrollbars=yes',
            'resizable=yes',
            'toolbar=no',
            'menubar=no',
            'location=no',
            'status=no'
        ].join(',');

        // Open popup
        this.popup = window.open(url, 'ebay_oauth', popupFeatures);

        if (!this.popup) {
            onError(new Error('Failed to open popup. Please allow popups for this site.'));
            return;
        }

        console.log('eBay OAuth popup opened');

        // Set up message listener for popup communication
        this.messageListener = (event) => {
            // Verify origin for security
            const allowedOrigins = [window.location.origin, 'https://local.lastseen.me:8085'];
            if (!allowedOrigins.includes(event.origin)) {
                return;
            }

            const { type, data, error } = event.data;

            if (type === 'ebay_oauth_success') {
                this.cleanup();
                onSuccess(data);
            } else if (type === 'ebay_oauth_error') {
                this.cleanup();
                onError(new Error(error));
            }
        };

        window.addEventListener('message', this.messageListener);

        // Check if popup is closed manually
        this.checkInterval = setInterval(() => {
            if (this.popup.closed) {
                this.cleanup();
                onCancel();
            }
        }, 1000);

        // Focus the popup
        this.popup.focus();
    }

    /**
     * Clean up popup and listeners
     */
    cleanup() {
        if (this.popup && !this.popup.closed) {
            this.popup.close();
        }
        this.popup = null;

        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }

        if (this.messageListener) {
            window.removeEventListener('message', this.messageListener);
            this.messageListener = null;
        }

        this.authState = null;
    }

    /**
     * Check if OAuth is in progress
     */
    isOAuthInProgress() {
        return this.popup !== null;
    }
}

/**
 * Utility function to create a simple OAuth button with built-in handling
 */
function setupEbayOAuthButton(buttonElement, options = {}) {
    const manager = new EbayOAuthManager();
    
    const defaultOptions = {
        onSuccess: (data) => {
            console.log('eBay OAuth successful:', data);
            alert('eBay authentication successful! Tokens have been saved.');
        },
        onError: (error) => {
            console.error('eBay OAuth error:', error);
            alert(`eBay authentication failed: ${error.message}`);
        },
        onCancel: () => {
            console.log('eBay OAuth cancelled by user');
        },
        loadingText: 'Authenticating...',
        originalText: buttonElement.textContent
    };

    const config = { ...defaultOptions, ...options };

    buttonElement.addEventListener('click', async (e) => {
        e.preventDefault();
        
        if (manager.isOAuthInProgress()) {
            return; // Already in progress
        }

        // Update button state
        const originalText = buttonElement.textContent;
        const originalDisabled = buttonElement.disabled;
        
        buttonElement.textContent = config.loadingText;
        buttonElement.disabled = true;

        try {
            await manager.startOAuthFlow({
                onSuccess: (data) => {
                    buttonElement.textContent = originalText;
                    buttonElement.disabled = originalDisabled;
                    config.onSuccess(data);
                },
                onError: (error) => {
                    buttonElement.textContent = originalText;
                    buttonElement.disabled = originalDisabled;
                    config.onError(error);
                },
                onCancel: () => {
                    buttonElement.textContent = originalText;
                    buttonElement.disabled = originalDisabled;
                    config.onCancel();
                }
            });
        } catch (error) {
            buttonElement.textContent = originalText;
            buttonElement.disabled = originalDisabled;
            config.onError(error);
        }
    });

    return manager;
}

// Export for use in other scripts
window.EbayOAuthManager = EbayOAuthManager;
window.setupEbayOAuthButton = setupEbayOAuthButton;