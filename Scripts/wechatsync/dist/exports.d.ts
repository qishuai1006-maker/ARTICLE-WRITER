declare class ExtensionBridge {
    private port;
    private wss;
    private httpServer;
    private client;
    private isServerMode;
    private pendingRequests;
    private requestTimeout;
    private connectionResolvers;
    private token;
    private silent;
    constructor(port?: number, options?: {
        silent?: boolean;
    });
    /**
     * 启动服务 - 自动选择服务器模式或客户端模式
     */
    start(): Promise<void>;
    /**
     * 启动 WebSocket 服务器 + HTTP API
     */
    private startServer;
    /**
     * 启动 HTTP API 服务器（供其他 MCP 实例调用）
     */
    private startHttpApi;
    /**
     * 停止服务器
     */
    stop(): void;
    /**
     * 检查 Extension 是否已连接
     */
    /**
     * 获取当前运行模式
     */
    getMode(): 'primary' | 'secondary';
    /**
     * 检查 Extension 是否已连接
     */
    isConnected(): boolean;
    /**
     * 等待 Extension 连接
     */
    waitForConnection(timeoutMs?: number): Promise<void>;
    /**
     * 检查 Primary 实例健康状态（Secondary 模式用）
     */
    private checkPrimaryHealth;
    /**
     * 发送请求到 Extension 并等待响应
     */
    request<T = unknown>(method: string, params?: Record<string, unknown>): Promise<T>;
    /**
     * SECONDARY 模式请求（带重试 + 自动接管）
     */
    private requestViaSecondary;
    /**
     * 尝试接管端口，升级为 PRIMARY
     */
    private tryPromote;
    /**
     * 直接通过 WebSocket 发送请求（服务器模式）
     */
    private requestInternal;
    /**
     * 通过 HTTP API 转发请求（客户端模式）
     */
    private requestViaHttp;
    /**
     * 处理来自 Extension 的消息
     */
    private handleMessage;
    /**
     * 生成唯一 ID
     */
    private generateId;
    private readonly CHUNK_SIZE;
    private readonly CHUNK_THRESHOLD;
    /**
     * 分片上传图片
     * 大于 1MB 的图片会自动分片上传
     */
    uploadImageChunked(imageData: string, mimeType: string, platform?: string): Promise<{
        url: string;
        platform: string;
    }>;
}

/**
 * MCP Server 与 Extension 通讯的消息类型
 */
interface RequestMessage {
    id: string;
    method: string;
    token?: string;
    params?: Record<string, unknown>;
}
interface ResponseMessage {
    id: string;
    result?: unknown;
    error?: {
        code: number;
        message: string;
    };
}
interface PlatformInfo {
    id: string;
    name: string;
    icon: string;
    homepage: string;
    isAuthenticated: boolean;
    username?: string;
    avatar?: string;
    error?: string;
}
interface SyncResult {
    platform: string;
    success: boolean;
    postId?: string;
    postUrl?: string;
    draftOnly?: boolean;
    error?: string;
    timestamp: number;
}

export { ExtensionBridge, type PlatformInfo, type RequestMessage, type ResponseMessage, type SyncResult };
