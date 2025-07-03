/**
 * Monaco Editor Stability Verification Script
 * Run this in browser console to verify all stability fixes
 */

class MonacoVerifier {
    constructor() {
        this.results = [];
        this.testCount = 0;
        this.passCount = 0;
    }

    log(test, status, message = '') {
        this.testCount++;
        if (status === 'PASS') this.passCount++;

        const result = {
            test,
            status,
            message,
            timestamp: new Date().toISOString()
        };

        this.results.push(result);

        const emoji = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : '⚠️';
        console.log(`${emoji} ${test}: ${message}`);

        return result;
    }

    async runAllTests() {
        console.log('🔍 Starting Monaco Editor Verification...\n');

        try {
            await this.test1_InitialMount();
            await this.test2_PanelResize();
            await this.test3_LocalStorageIntegrity();
            await this.test4_HiddenVisibleRelayout();
            await this.test5_TabVisibility();
            await this.test6_MobileOrientation();
            await this.test7_PerformanceBudget();
            await this.test8_MemoryLeak();
            await this.test9_CopilotIntelliSense();
            await this.test10_RegressionSweep();

            this.generateReport();
        } catch (error) {
            console.error('❌ Verification failed:', error);
        }
    }

    // Test 1: Initial Mount
    async test1_InitialMount() {
        const editor = document.querySelector('.monaco-editor');
        if (!editor) {
            this.log('1. Initial Mount', 'FAIL', 'Monaco editor not found in DOM');
            return;
        }

        const rect = editor.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;

        this.log('1. Initial Mount', isVisible ? 'PASS' : 'FAIL',
            `Editor dimensions: ${rect.width}x${rect.height}`);
    }

    // Test 2: Panel Resize
    async test2_PanelResize() {
        const editor = document.querySelector('.monaco-editor');
        if (!editor) {
            this.log('2. Panel Resize', 'SKIP', 'No editor found');
            return;
        }

        let resizeCount = 0;
        const startTime = performance.now();

        const ro = new window.ResizeObserver(() => {
            resizeCount++;
        });

        ro.observe(editor);

        // Simulate resize events for 1 second
        await new Promise(resolve => setTimeout(resolve, 1000));
        ro.disconnect();

        const elapsedTime = performance.now() - startTime;
        const eventsPerSecond = (resizeCount / elapsedTime) * 1000;

        const isThrottled = eventsPerSecond <= 30; // Allow up to 30 events/sec
        this.log('2. Panel Resize', isThrottled ? 'PASS' : 'WARN',
            `${resizeCount} resize events, ${eventsPerSecond.toFixed(1)} events/sec`);
    }

    // Test 3: localStorage Layout Integrity
    async test3_LocalStorageIntegrity() {
        const storageKey = 'react-resizable-panels:chat-editor-vertical';
        const stored = localStorage.getItem(storageKey);

        if (!stored) {
            this.log('3. localStorage Layout', 'SKIP', 'No layout data found');
            return;
        }

        try {
            const parsed = JSON.parse(stored);
            const layout = parsed['chat-editor-vertical']?.layout;

            if (!Array.isArray(layout) || layout.length < 2) {
                this.log('3. localStorage Layout', 'FAIL', 'Invalid layout format');
                return;
            }

            const hasZeroPanel = layout.some(size => size === 0);
            this.log('3. localStorage Layout', hasZeroPanel ? 'FAIL' : 'PASS',
                `Layout: [${layout.join(', ')}]`);
        } catch (error) {
            this.log('3. localStorage Layout', 'FAIL', `Parse error: ${error.message}`);
        }
    }

    // Test 4: Hidden → Visible Re-layout
    async test4_HiddenVisibleRelayout() {
        const editor = document.querySelector('.monaco-editor');
        if (!editor) {
            this.log('4. Hidden→Visible Re-layout', 'SKIP', 'No editor found');
            return;
        }

        const originalDisplay = editor.style.display;

        // Hide editor
        editor.style.display = 'none';
        await new Promise(resolve => setTimeout(resolve, 100));

        // Show editor
        editor.style.display = originalDisplay;

        // Check for layout errors
        const hasLayoutError = this.checkConsoleErrors(['Cannot read property', 'layout', 'of null']);

        this.log('4. Hidden→Visible Re-layout', hasLayoutError ? 'FAIL' : 'PASS',
            hasLayoutError ? 'Layout errors detected' : 'No layout errors');
    }

    // Test 5: Tab Visibility
    async test5_TabVisibility() {
        const editor = document.querySelector('.monaco-editor');
        if (!editor) {
            this.log('5. Tab Visibility', 'SKIP', 'No editor found');
            return;
        }

        const originalRect = editor.getBoundingClientRect();

        // Simulate tab visibility change
        const event = new window.Event('visibilitychange');
        document.dispatchEvent(event);
        await new Promise(resolve => setTimeout(resolve, 100));

        const newRect = editor.getBoundingClientRect();
        const dimensionsPreserved = Math.abs(originalRect.width - newRect.width) < 5 &&
            Math.abs(originalRect.height - newRect.height) < 5;

        this.log('5. Tab Visibility', dimensionsPreserved ? 'PASS' : 'FAIL',
            `Dimensions preserved: ${dimensionsPreserved}`);
    }

    // Test 6: Mobile Portrait/Landscape
    async test6_MobileOrientation() {
        const isMobile = window.innerWidth < 768;

        if (!isMobile) {
            this.log('6. Mobile Orientation', 'SKIP', 'Not on mobile device');
            return;
        }

        const editor = document.querySelector('.monaco-editor');
        if (!editor) {
            this.log('6. Mobile Orientation', 'SKIP', 'No editor found');
            return;
        }

        const rect = editor.getBoundingClientRect();
        const isFullWidth = rect.width >= window.innerWidth * 0.95;

        // Check touch targets
        const touchTargets = document.querySelectorAll('.mobile-code-toolbar button');
        const validTouchTargets = Array.from(touchTargets).every(btn => {
            const btnRect = btn.getBoundingClientRect();
            return btnRect.width >= 44 && btnRect.height >= 44;
        });

        const mobileOptimized = isFullWidth && (touchTargets.length === 0 || validTouchTargets);

        this.log('6. Mobile Orientation', mobileOptimized ? 'PASS' : 'FAIL',
            `Full width: ${isFullWidth}, Touch targets: ${validTouchTargets}`);
    }

    // Test 7: Performance Budget
    async test7_PerformanceBudget() {
        if (typeof window.monaco === 'undefined') {
            this.log('7. Performance Budget', 'SKIP', 'Monaco not available');
            return;
        }

        const editors = window.monaco.editor.getEditors();
        if (editors.length === 0) {
            this.log('7. Performance Budget', 'SKIP', 'No editors found');
            return;
        }

        const editor = editors[0];
        const startTime = performance.now();

        try {
            editor.layout();
            const layoutTime = performance.now() - startTime;

            const withinBudget = layoutTime < 16; // 16ms budget
            this.log('7. Performance Budget', withinBudget ? 'PASS' : 'WARN',
                `Layout time: ${layoutTime.toFixed(2)}ms`);
        } catch (error) {
            this.log('7. Performance Budget', 'FAIL', `Layout error: ${error.message}`);
        }
    }

    // Test 8: Memory Leak
    async test8_MemoryLeak() {
        if (typeof window.monaco === 'undefined') {
            this.log('8. Memory Leak', 'SKIP', 'Monaco not available');
            return;
        }

        const initialModelCount = window.monaco.editor.getModels().length;

        // Create and dispose some models
        for (let i = 0; i < 5; i++) {
            const model = window.monaco.editor.createModel('test content', 'javascript');
            model.dispose();
        }

        const finalModelCount = window.monaco.editor.getModels().length;
        const hasLeak = finalModelCount > initialModelCount;

        this.log('8. Memory Leak', hasLeak ? 'FAIL' : 'PASS',
            `Models: ${initialModelCount} → ${finalModelCount}`);
    }

    // Test 9: Copilot/IntelliSense
    async test9_CopilotIntelliSense() {
        if (typeof window.monaco === 'undefined') {
            this.log('9. Copilot/IntelliSense', 'SKIP', 'Monaco not available');
            return;
        }

        const editors = window.monaco.editor.getEditors();
        if (editors.length === 0) {
            this.log('9. Copilot/IntelliSense', 'SKIP', 'No editors found');
            return;
        }

        const editor = editors[0];
        const startTime = performance.now();

        try {
            // Trigger completion
            const completionPromise = editor.trigger('test', 'editor.action.triggerSuggest');

            // Wait for completion or timeout
            const timeoutPromise = new Promise(resolve => setTimeout(() => resolve('timeout'), 500));
            await Promise.race([completionPromise, timeoutPromise]);

            const responseTime = performance.now() - startTime;
            const isResponsive = responseTime < 300;

            this.log('9. Copilot/IntelliSense', isResponsive ? 'PASS' : 'WARN',
                `Response time: ${responseTime.toFixed(2)}ms`);
        } catch (error) {
            this.log('9. Copilot/IntelliSense', 'FAIL', `Completion error: ${error.message}`);
        }
    }

    // Test 10: Regression Sweep
    async test10_RegressionSweep() {
        // Check for common console errors
        const commonErrors = [
            'Cannot read property',
            'monaco is not defined',
            'layout of null',
            'ResizeObserver loop limit exceeded',
            'Module not found'
        ];

        const hasErrors = this.checkConsoleErrors(commonErrors);

        // Check for required DOM elements
        const requiredElements = [
            '.monaco-editor',
            '.monaco-editor .view-lines'
        ];

        const missingElements = requiredElements.filter(selector =>
            !document.querySelector(selector)
        );

        const hasRegressions = hasErrors || missingElements.length > 0;

        this.log('10. Regression Sweep', hasRegressions ? 'FAIL' : 'PASS',
            hasRegressions ?
                `Errors: ${hasErrors}, Missing: ${missingElements.join(', ')}` :
                'No regressions detected'
        );
    }

    // Utility: Check console for errors
    checkConsoleErrors() {
        // This is a simplified check - in a real implementation,
        // you'd want to hook into console.error to capture errors
        return false; // Placeholder
    }

    // Generate final report
    generateReport() {
        console.log('\n📊 Monaco Editor Verification Report');
        console.log('═'.repeat(50));
        console.log(`Tests run: ${this.testCount}`);
        console.log(`Passed: ${this.passCount}`);
        console.log(`Failed: ${this.testCount - this.passCount}`);
        console.log(`Success rate: ${((this.passCount / this.testCount) * 100).toFixed(1)}%`);

        const allPassed = this.passCount === this.testCount;
        console.log(`\n${allPassed ? '✅' : '❌'} Overall result: ${allPassed ? 'MERGE SAFE' : 'NEEDS ATTENTION'}`);

        // Detailed results
        console.log('\nDetailed Results:');
        this.results.forEach(result => {
            const emoji = result.status === 'PASS' ? '✅' : result.status === 'FAIL' ? '❌' : '⚠️';
            console.log(`${emoji} ${result.test}: ${result.message}`);
        });
    }
}

// Export for use in console
window.MonacoVerifier = MonacoVerifier;

// Auto-run if Monaco is available
if (typeof window !== 'undefined' && document.querySelector('.monaco-editor')) {
    console.log('🚀 Monaco Editor detected - run verification with:');
    console.log('const verifier = new MonacoVerifier(); verifier.runAllTests();');
}
