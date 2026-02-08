import * as vscode from 'vscode';
import { TrinityClient } from '../core/TrinityClient';
import { ProcessManager } from '../services/ProcessManager';

/**
 * TrinityPanelManager - Opens 8810 as an Editor Tab (WebviewPanel)
 * SOTA 2026: No WebSocket - Uses ProcessManager events directly.
 */
export class TrinityPanelManager {
    private _panel?: vscode.WebviewPanel;
    private _client?: TrinityClient;
    private _extensionUri: vscode.Uri;
    private _workspacePath?: string;
    private _onStartRequest: () => void;
    private _onStopRequest: () => void;
    private _getProcessManager: () => ProcessManager | undefined;

    constructor(
        extensionUri: vscode.Uri,
        onStartRequest: () => void,
        onStopRequest: () => void,
        getProcessManager: () => ProcessManager | undefined,
        workspacePath?: string
    ) {
        this._extensionUri = extensionUri;
        this._workspacePath = workspacePath;
        this._onStartRequest = onStartRequest;
        this._onStopRequest = onStopRequest;
        this._getProcessManager = getProcessManager;
    }

    /**
     * Show the panel. Creates it if not existing, or reveals it if already open.
     */
    public async show() {
        if (this._panel) {
            this._panel.reveal(vscode.ViewColumn.One);
            return;
        }

        // SOTA 2026: Use workspace assets path for videos (not bundled in VSIX)
        const assetsUri = this._workspacePath
            ? vscode.Uri.file(require('path').join(this._workspacePath, 'social', 'assets'))
            : vscode.Uri.joinPath(this._extensionUri, '..', 'assets');

        this._panel = vscode.window.createWebviewPanel(
            'trinity8810',
            '🧬 Trinity 8810',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                // Note: Autoplay works because videos are muted in AngelPlayer.tsx
                localResourceRoots: [
                    vscode.Uri.joinPath(this._extensionUri, 'out'),
                    assetsUri,
                ],
            }
        );

        this._panel.iconPath = vscode.Uri.joinPath(assetsUri, 'images', 'icon.webp');
        this._panel.webview.html = this.getHtmlForWebview(this._panel.webview, assetsUri);

        // Client Initialization (SOTA 2026: No WebSocket - uses ProcessManager events)
        this._client = new TrinityClient({
            postMessage: (msg) => {
                // SOTA 2026 FIX: Always send messages (status must sync even before panel is fully visible)
                try {
                    this._panel?.webview.postMessage(msg).then(undefined, (err: Error) => {
                        // Suppress disposal errors typically caused by race conditions on close
                    });
                } catch (e) {
                    // Ignore sync errors
                }
            },
            onStartRequest: () => this._onStartRequest(),
            onStopRequest: () => this._onStopRequest(),
            getProcessManager: () => this._getProcessManager()
        });

        this._panel.webview.onDidReceiveMessage((message: any) => {
            this._client?.handleMessage(message);
        });

        this._panel.onDidDispose(() => {
            this._client?.dispose();
            this._client = undefined;
            this._panel = undefined;
        });

        // Start connection
        this._client.start();

        // SOTA 2026: Port Forwarding for Remote SSH/Codespaces
        // The asExternalUri() call triggers VSCode's automatic port forwarding.
        // We DON'T use the result for the iframe (it stays localhost:8089),
        // but the call itself creates the SSH tunnel so localhost works in the webview.
        try {
            const localUri = vscode.Uri.parse('http://127.0.0.1:8089');
            await vscode.env.asExternalUri(localUri);
            // Port forwarding now active - localhost:8089 will tunnel to remote
        } catch (e) {
            console.warn('[Trinity] Port forwarding trigger failed:', e);
        }
    }

    private getHtmlForWebview(webview: vscode.Webview, assetsUri: vscode.Uri) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'out', 'webview', 'assets', 'index.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'out', 'webview', 'assets', 'index.css'));

        // SOTA 2026: All video URIs for VideoEngine (from workspace assets)
        const videoUris = {
            init: webview.asWebviewUri(vscode.Uri.joinPath(assetsUri, 'videos', 'initialisation.webm')),
            idle1: webview.asWebviewUri(vscode.Uri.joinPath(assetsUri, 'videos', 'idle1.webm')),
            idle2: webview.asWebviewUri(vscode.Uri.joinPath(assetsUri, 'videos', 'idle2.webm')),
            idle3: webview.asWebviewUri(vscode.Uri.joinPath(assetsUri, 'videos', 'idle3.webm')),
            angel: webview.asWebviewUri(vscode.Uri.joinPath(assetsUri, 'videos', 'angel.webm')),
        };
        const nonce = getNonce();


        // SOTA 2026: Dynamic Port Forwarding
        // This calculates the correct external URI for the iframe (e.g. if running in Codespaces or Remote SSH)
        const localUrl = 'http://127.0.0.1:8089';
        // We'll trust the process to inject this via a postMessage later if needed,
        // or we can pre-calculate it here and pass it via window.trinityConfig.

        return `<!DOCTYPE html>
<html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; font-src ${webview.cspSource}; img-src ${webview.cspSource} data:; media-src ${webview.cspSource}; frame-src http://localhost:* http://127.0.0.1:* https://*.github.dev https://*.gitpod.io;">
                <link rel="stylesheet" type="text/css" href="${styleUri}" />
                <title>Trinity 8810</title>
            </head>
            <body>
                <div id="root"></div>
                <script nonce="${nonce}">
                    window.videoUris = {
                        init: "${videoUris.init}",
                        idle1: "${videoUris.idle1}",
                        idle2: "${videoUris.idle2}",
                        idle3: "${videoUris.idle3}",
                        angel: "${videoUris.angel}"
                    };
                    window.angelVideoUri = "${videoUris.angel}";
                    window.trinityBaseUrl = "${localUrl}"; 
                </script>
                <script type="module" nonce="${nonce}" src="${scriptUri}"></script>
            </body>
            </html>`;
    }

    /**
     * SOTA 2026: Public method to send messages to webview (for sentinel buttons)
     */
    public postMessage(message: any) {
        try {
            this._panel?.webview.postMessage(message);
        } catch {
            // Ignore if panel is disposed
        }
    }

    public dispose() {
        this._client?.dispose();
        this._panel?.dispose();
    }
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
