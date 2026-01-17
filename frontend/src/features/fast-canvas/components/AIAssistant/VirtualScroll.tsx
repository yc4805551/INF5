import React, { useState, useRef, useEffect } from 'react';

interface VirtualScrollProps<T> {
    items: T[];
    itemHeight: number;
    containerHeight: number;
    renderItem: (item: T, index: number) => React.ReactNode;
    overscan?: number;
}

/**
 * 轻量级虚拟滚动组件
 * 只渲染可见区域 + overscan 的项目，大幅提升长列表性能
 */
export function VirtualScroll<T>({
    items,
    itemHeight,
    containerHeight,
    renderItem,
    overscan = 3
}: VirtualScrollProps<T>) {
    const [scrollTop, setScrollTop] = useState(0);
    const containerRef = useRef<HTMLDivElement>(null);

    const totalHeight = items.length * itemHeight;

    // 计算可见范围
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
        items.length - 1,
        Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );

    const visibleItems = items.slice(startIndex, endIndex + 1);
    const offsetY = startIndex * itemHeight;

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const handleScroll = () => {
            setScrollTop(container.scrollTop);
        };

        container.addEventListener('scroll', handleScroll);
        return () => container.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div
            ref={containerRef}
            style={{
                height: containerHeight,
                overflow: 'auto',
                position: 'relative'
            }}
        >
            {/* Spacer to maintain scroll height */}
            <div style={{ height: totalHeight, position: 'relative' }}>
                {/* Visible items container */}
                <div style={{ transform: `translateY(${offsetY}px)` }}>
                    {visibleItems.map((item, index) => (
                        <div key={startIndex + index} style={{ height: itemHeight }}>
                            {renderItem(item, startIndex + index)}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
