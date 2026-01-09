/**
 * NotificationContainer component
 * Displays toast notifications
 */

import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore, type Notification } from '@/stores';

/**
 * Notification icon by type
 */
const notificationIcons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

/**
 * Notification colors by type
 */
const notificationColors = {
  success: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    icon: 'text-green-500',
    title: 'text-green-800',
    message: 'text-green-700',
  },
  error: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: 'text-red-500',
    title: 'text-red-800',
    message: 'text-red-700',
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    icon: 'text-yellow-500',
    title: 'text-yellow-800',
    message: 'text-yellow-700',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: 'text-blue-500',
    title: 'text-blue-800',
    message: 'text-blue-700',
  },
};

/**
 * Single notification toast
 */
interface NotificationToastProps {
  notification: Notification;
  onDismiss: (id: string) => void;
}

function NotificationToast({ notification, onDismiss }: NotificationToastProps) {
  const Icon = notificationIcons[notification.type];
  const colors = notificationColors[notification.type];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={clsx(
        'flex items-start gap-3 rounded-lg border p-4 shadow-lg',
        colors.bg,
        colors.border
      )}
    >
      <Icon className={clsx('h-5 w-5 flex-shrink-0', colors.icon)} />
      <div className="flex-1 min-w-0">
        <p className={clsx('text-sm font-medium', colors.title)}>
          {notification.title}
        </p>
        {notification.message && (
          <p className={clsx('mt-1 text-sm', colors.message)}>
            {notification.message}
          </p>
        )}
      </div>
      {notification.dismissible !== false && (
        <button
          onClick={() => onDismiss(notification.id)}
          className="flex-shrink-0 rounded-lg p-1 hover:bg-white/50 transition-colors"
        >
          <X className="h-4 w-4 text-gray-400" />
        </button>
      )}
    </motion.div>
  );
}

/**
 * Notification container component
 */
export function NotificationContainer() {
  const notifications = useUIStore((state) => state.notifications);
  const removeNotification = useUIStore((state) => state.removeNotification);

  return (
    <div className="fixed right-4 top-20 z-50 flex flex-col gap-2 w-full max-w-sm">
      <AnimatePresence mode="popLayout">
        {notifications.map((notification) => (
          <NotificationToast
            key={notification.id}
            notification={notification}
            onDismiss={removeNotification}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

export default NotificationContainer;
