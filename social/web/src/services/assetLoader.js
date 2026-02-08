/**
 * SOTA 2026: Asset Loader Service (Pure Web)
 * All assets served directly from public folder.
 */

class AssetLoaderService {
    /**
     * Smart Resolve: Returns the direct public path for a video.
     * SOTA 2026: Pure web - all files served from /videos/
     */
    async getSmartPath(filename) {
        if (!filename) return null;
        return `/videos/${filename}`;
    }
}

export const assetLoader = new AssetLoaderService();
