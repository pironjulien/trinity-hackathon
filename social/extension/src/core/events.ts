/**
 * Trinity Control Center - Typed Event Emitter
 * Type-safe event handling for monitoring and state updates
 */

import { EventEmitter } from 'events';
import type { TrinityEvents } from './types';

type EventKey = keyof TrinityEvents;

/**
 * Type-safe EventEmitter wrapper for Trinity events
 */
export class TrinityEventEmitter {
    private emitter = new EventEmitter();

    /**
     * Subscribe to an event
     */
    on<K extends EventKey>(event: K, listener: (data: TrinityEvents[K]) => void): this {
        this.emitter.on(event, listener);
        return this;
    }

    /**
     * Subscribe to an event (once)
     */
    once<K extends EventKey>(event: K, listener: (data: TrinityEvents[K]) => void): this {
        this.emitter.once(event, listener);
        return this;
    }

    /**
     * Unsubscribe from an event
     */
    off<K extends EventKey>(event: K, listener: (data: TrinityEvents[K]) => void): this {
        this.emitter.off(event, listener);
        return this;
    }

    /**
     * Emit an event
     */
    emit<K extends EventKey>(event: K, data: TrinityEvents[K]): boolean {
        return this.emitter.emit(event, data);
    }

    /**
     * Remove all listeners
     */
    removeAllListeners(event?: EventKey): this {
        if (event) {
            this.emitter.removeAllListeners(event);
        } else {
            this.emitter.removeAllListeners();
        }
        return this;
    }

    /**
     * Get listener count
     */
    listenerCount(event: EventKey): number {
        return this.emitter.listenerCount(event);
    }
}

/**
 * Singleton instance for global event bus
 */
export const trinityEvents = new TrinityEventEmitter();
