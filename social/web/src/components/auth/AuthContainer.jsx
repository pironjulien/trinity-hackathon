import { AnimatePresence, motion } from 'framer-motion'; // eslint-disable-line no-unused-vars

// SOTA 2026: Video Authentication Interface
import SceneContainer from '../SceneContainer';

/**
 * AuthContainer - SOTA 2026
 * Manages the Authentication Reality.
 */
export default function AuthContainer({ usernameRef, passwordRef, onLogin, isLoading }) {
    // Singular Reality: Video Auth
    const ActiveComponent = SceneContainer;

    return (
        <div className="fixed inset-0 z-[100] w-full h-full text-white overflow-hidden font-mono">
            <AnimatePresence mode="wait">
                <motion.div
                    key="chaos-engine"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 1 }}
                    className="w-full h-full"
                >
                    <ActiveComponent
                        usernameRef={usernameRef} // Pass ref down
                        passwordRef={passwordRef} // Pass ref down
                        onLogin={onLogin}
                        isLoading={isLoading}
                    />
                </motion.div>
            </AnimatePresence>
        </div>
    );
}
