# -*- coding: utf-8 -*-
__author__ = "Lit"
__version__ = "1.0.6"

"""
Version 1.0.0
* Bootstrap 5 and ECharts 5 UI
* Light/dark theme support
* Professional testing report layout
* Responsive design
* Statistic cards and chart visualization
* Pass-rate doughnut chart
* Skipped test display
* Copyable test details
* Optimized chart labels
* Author: Lit

"""

# TODO: color stderr
# TODO: simplify javascript using ,ore than 1 class in the class attribute?

import datetime
import sys
import io
import os
import time
import webbrowser
import unittest
from xml.sax import saxutils
import base64
import json
from io import BytesIO


# ------------------------------------------------------------------------
# The redirectors below are used to capture output during testing. Output
# sent to sys.stdout and sys.stderr are automatically captured. However
# in some cases sys.stdout is already cached before HTMLTestRunner is
# invoked (e.g. calling logging.basicConfig). In order to capture those
# output, use the redirectors for the cached stream.
#
# e.g.
#   >>> logging.basicConfig(stream=HTMLTestRunner.stdout_redirector)
#   >>>

class OutputRedirector(object):
    """ Wrapper to redirect stdout or stderr """
    def __init__(self, fp):
        self.fp = fp

    def write(self, s):
        self.fp.write(s)

    def writelines(self, lines):
        self.fp.writelines(lines)

    def flush(self):
        self.fp.flush()

stdout_redirector = OutputRedirector(sys.stdout)
stderr_redirector = OutputRedirector(sys.stderr)


# ------------------------------------------------------------------------
# Screenshot Manager
#

class ScreenshotManager:
    """Screenshot manager: convert supported image sources to base64."""
    
    @staticmethod
    def to_base64(image_source, description=""):
        """Convert a supported image source to a base64 screenshot dictionary."""
        try:
            # 1. File path
            if isinstance(image_source, str):
                if os.path.exists(image_source):
                    with open(image_source, 'rb') as f:
                        img_data = f.read()
                    return {
                        'data': base64.b64encode(img_data).decode('utf-8'),
                        'description': description or os.path.basename(image_source)
                    }
            
            # 2. Raw bytes
            elif isinstance(image_source, bytes):
                return {
                    'data': base64.b64encode(image_source).decode('utf-8'),
                    'description': description or 'Screenshot'
                }
            
            # 3. PIL Image
            elif hasattr(image_source, 'save'):
                buffer = BytesIO()
                image_source.save(buffer, format='PNG')
                img_data = buffer.getvalue()
                return {
                    'data': base64.b64encode(img_data).decode('utf-8'),
                    'description': description or 'PIL Image'
                }
            
            # 4. Selenium WebDriver
            elif hasattr(image_source, 'get_screenshot_as_png'):
                img_data = image_source.get_screenshot_as_png()
                return {
                    'data': base64.b64encode(img_data).decode('utf-8'),
                    'description': description or 'Selenium Screenshot'
                }
                
        except Exception as e:
            sys.stderr.write(f"截图转换失败: {e}\n")
            return None
        
        return None


# Global reference to the active TestResult instance.
_current_result = None


def attach_screenshot(image_source, description=""):
    """Attach a screenshot to the currently running test case."""
    if _current_result:
        _current_result.attach_screenshot(image_source, description)
    else:
        sys.stderr.write("警告: 无法添加截图，当前没有正在运行的测试\n")


# ----------------------------------------------------------------------
# Template


class Template_mixin(object):
    """
    Define a HTML template for report customerization and generation.

    Overall structure of an HTML report

    HTML
    +------------------------+
    |<html>                  |
    |  <head>                |
    |                        |
    |   STYLESHEET           |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |  </head>               |
    |                        |
    |  <body>                |
    |                        |
    |   HEADING              |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |   REPORT               |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |   ENDING               |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |  </body>               |
    |</html>                 |
    +------------------------+
    """

    STATUS = {
        0: '通过',
        1: '失败',
        2: '错误',
        3: '跳过',
    }

    DEFAULT_TITLE = 'Unit Test Report'
    DEFAULT_DESCRIPTION = ''

    # ------------------------------------------------------------------------
    # HTML Template

    HTML_TMPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="%(generator)s"/>
    <title>%(title)s</title>
    
    <!-- Bootstrap 5.3 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <!-- Element Plus visual tokens -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/element-plus@2.13.3/dist/index.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/inter@5.2.8/index.min.css">
    <!-- ECharts 5.x -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <!-- Page capture -->
    <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
    <!-- Bootstrap 5 JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    %(stylesheet)s
    
</head>
<body>
    <script type="text/javascript">
    /* level - 0:Summary; 1:Failed; 2:All */
    function showCase(level) {
        const trs = document.getElementsByTagName("tr");
        for (let i = 0; i < trs.length; i++) {
            const tr = trs[i];
            const id = tr.id;
            // ft: fail test, pt: pass test, st: skip test
            if (id.substr(0,2) === 'ft') {
                // Failed/error rows are hidden in summary and visible in failed/all views.
                tr.style.display = level < 1 ? 'none' : 'table-row';
            }
            if (id.substr(0,2) === 'pt') {
                // Passed rows are only visible in all view.
                tr.style.display = level > 1 ? 'table-row' : 'none';
            }
            if (id.substr(0,2) === 'st') {
                // Skipped rows are only visible in all view.
                tr.style.display = level > 1 ? 'table-row' : 'none';
            }
        }
        
        // Update active filter button.
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }

    function showClassDetail(cid, count) {
        // Find the first test row to decide whether the class is expanded.
        const tid0 = 't' + cid.substr(1) + '.1';
        let firstTid = 'f' + tid0;
        let firstElem = document.getElementById(firstTid);
        if (!firstElem) {
            firstTid = 'p' + tid0;
            firstElem = document.getElementById(firstTid);
        }
        
        if (!firstElem) return;
        
        // Toggle all test rows in this class.
        const isHidden = firstElem.style.display === 'none' || firstElem.style.display === '';
        
        // Toggle visibility for each test row.
        for (let i = 0; i < count; i++) {
            const tid0 = 't' + cid.substr(1) + '.' + (i+1);
            let tid = 'f' + tid0;
            let elem = document.getElementById(tid);
            if (!elem) {
                tid = 'p' + tid0;
                elem = document.getElementById(tid);
            }
            
            if (elem) {
                elem.style.display = isHidden ? 'table-row' : 'none';
                // Hide detail panels when collapsing rows.
                const divElem = document.getElementById('div_' + tid);
                if (divElem && !isHidden) {
                    divElem.style.display = 'none';
                }
            }
        }
    }

    function showTestDetail(div_id){
        const details_div = document.getElementById(div_id);
        const displayState = details_div.style.display;
        details_div.style.display = (displayState !== 'table-row') ? 'table-row' : 'none';
    }

    function toggleAllDetails(button) {
        const detailRows = Array.from(document.querySelectorAll('.detail-row'));
        const shouldExpand = detailRows.some(row => row.style.display === 'none' || row.style.display === '');
        detailRows.forEach(row => {
            row.style.display = shouldExpand ? 'table-row' : 'none';
        });
        if (button) {
            button.classList.toggle('detail-active', shouldExpand);
            const label = button.querySelector('.tool-label');
            if (label) label.textContent = shouldExpand ? '收起详情' : '展开详情';
        }
    }

    function savePageScreenshot() {
        const target = document.querySelector('.pt-main');
        if (!target || typeof html2canvas === 'undefined') {
            alert('截图组件未加载，请稍后重试');
            return;
        }
        html2canvas(target, {
            backgroundColor: getComputedStyle(document.body).backgroundColor,
            scale: Math.min(window.devicePixelRatio || 1, 2),
            useCORS: true
        }).then(canvas => {
            const link = document.createElement('a');
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            link.download = 'test-report-' + timestamp + '.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        });
    }

    function exportPdf() {
        window.print();
    }
    
    // Copy test detail content.
    function copyTestDetail(contentId, button) {
        const content = document.getElementById(contentId);
        if (!content) return;
        
        const text = content.textContent;
        
        // Use Clipboard API when available.
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                showCopySuccess(button);
            }).catch(() => {
                // Fallback for older browsers.
                fallbackCopy(text, button);
            });
        } else {
            // Fallback for older browsers.
            fallbackCopy(text, button);
        }
    }
    
    // Fallback copy method.
    function fallbackCopy(text, button) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopySuccess(button);
        } catch (err) {
            console.error('复制失败:', err);
        }
        document.body.removeChild(textarea);
    }
    
    // Show copy success state.
    function showCopySuccess(button) {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="bi bi-check-lg"></i> 已复制';
        button.classList.add('copy-success');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copy-success');
        }, 2000);
    }
    
    // Theme toggle.
    function toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Recreate chart after theme changes.
        const chart = echarts.getInstanceByDom(document.getElementById('chart'));
        if (chart) {
            chart.dispose();
        }
        const suiteChart = echarts.getInstanceByDom(document.getElementById('suiteChart'));
        if (suiteChart) {
            suiteChart.dispose();
        }
        initChart();
    }
    
    // Restore saved theme on page load.
    document.addEventListener('DOMContentLoaded', function() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-bs-theme', savedTheme);
    });
    </script>

    <main class="pt-main">
        <div class="container-fluid pt-content">
            %(heading)s
            %(report)s
        </div>
    </main>
    %(ending)s
    %(chart_script)s
</body>
</html>
"""  # variables: (title, generator, stylesheet, heading, report, ending, chart_script)

    ECHARTS_SCRIPT = """
    <script type="text/javascript">
    function initChart() {
        const chartDom = document.getElementById('chart');
        const myChart = echarts.init(chartDom);
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        
        const passCount = %(Pass)s;
        const failCount = %(fail)s;
        const errorCount = %(error)s;
        const skipCount = %(skip)s;
        const suiteStats = %(suite_stats)s;
        const total = passCount + failCount + errorCount + skipCount;
        const passRate = total > 0 ? ((passCount / total) * 100).toFixed(1) : 0;

        const option = {
            title: {
                text: passRate + '%%',
                subtext: '通过率',
                left: 'center',
                top: '35%%',
                textStyle: {
                    fontSize: 28,
                    fontWeight: 700,
                    color: isDark ? '#e8e8e8' : '#262626'
                },
                subtextStyle: {
                    fontSize: 12,
                    color: isDark ? '#a6a6a6' : '#8c8c8c',
                    lineHeight: 20
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%%)',
                backgroundColor: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
                borderColor: isDark ? '#434343' : '#d9d9d9',
                borderWidth: 1,
                textStyle: {
                    color: isDark ? '#e8e8e8' : '#262626',
                    fontSize: 13
                }
            },
            legend: {
                orient: 'horizontal',
                bottom: 2,
                left: 'center',
                itemGap: 10,
                itemWidth: 14,
                itemHeight: 8,
                textStyle: {
                    fontSize: 11,
                    color: isDark ? '#e8e8e8' : '#262626'
                },
                data: ['通过', '失败', '错误', '跳过'],
                formatter: function(name) {
                    const dataMap = {
                        '通过': passCount,
                        '失败': failCount,
                        '错误': errorCount,
                        '跳过': skipCount
                    };
                    return name + ': ' + dataMap[name];
                }
            },
            series: [
                {
                    name: '测试结果',
                    type: 'pie',
                    radius: ['48%%', '65%%'],
                    center: ['50%%', '43%%'],
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: 4,
                        borderColor: isDark ? '#141414' : '#fff',
                        borderWidth: 2
                    },
                    label: {
                        show: false,
                        position: 'outside',
                        formatter: function(params) {
                            if (params.value === 0) {
                                return '';  // Hide zero-value labels.
                            }
                            return params.name + '\\n' + params.value + ' (' + params.percent + '%%)';
                        },
                        fontSize: 13,
                        fontWeight: 500,
                        color: isDark ? '#e8e8e8' : '#262626',
                        distanceToLabelLine: 5
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 14,
                            fontWeight: 600
                        },
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.2)'
                        },
                        scale: true,
                        scaleSize: 5
                    },
                    labelLine: {
                        show: false,
                        length: 15,
                        length2: 24,
                        smooth: true,
                        lineStyle: {
                            color: isDark ? '#434343' : '#d9d9d9',
                            width: 1
                        }
                    },
                    data: [
                        {
                            value: passCount,
                            name: '通过',
                            itemStyle: { color: '#52c41a' }
                        },
                        {
                            value: failCount,
                            name: '失败',
                            itemStyle: { color: '#faad14' }
                        },
                        {
                            value: errorCount,
                            name: '错误',
                            itemStyle: { color: '#f5222d' }
                        },
                        {
                            value: skipCount,
                            name: '跳过',
                            itemStyle: { color: '#1890ff' }
                        }
                    ],
                    animationType: 'scale',
                    animationEasing: 'cubicOut',
                    animationDelay: function (idx) {
                        return idx * 100;
                    }
                }
            ]
        };

        myChart.setOption(option);

        const suiteChartDom = document.getElementById('suiteChart');
        if (suiteChartDom) {
            const suiteChart = echarts.init(suiteChartDom);
            const suiteNames = suiteStats.map(item => item.name);
            const suiteOption = {
                color: ['#52c41a', '#faad14', '#f5222d', '#1890ff'],
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    backgroundColor: isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)',
                    borderColor: isDark ? '#434343' : '#d9d9d9',
                    borderWidth: 1,
                    textStyle: {
                        color: isDark ? '#e8e8e8' : '#262626',
                        fontSize: 12
                    }
                },
                legend: {
                    top: 0,
                    right: 8,
                    itemGap: 10,
                    itemWidth: 14,
                    itemHeight: 8,
                    textStyle: {
                        fontSize: 11,
                        color: isDark ? '#e8e8e8' : '#262626'
                    },
                    data: ['通过', '失败', '错误', '跳过']
                },
                grid: {
                    left: 10,
                    right: 14,
                    top: 34,
                    bottom: 10,
                    containLabel: true
                },
                xAxis: {
                    type: 'value',
                    axisLabel: {
                        color: isDark ? '#a6a6a6' : '#64748b',
                        fontSize: 10
                    },
                    splitLine: {
                        lineStyle: {
                            color: isDark ? '#2f3746' : '#edf2f7'
                        }
                    }
                },
                yAxis: {
                    type: 'category',
                    data: suiteNames,
                    axisLabel: {
                        color: isDark ? '#e8e8e8' : '#262626',
                        fontSize: 10,
                        width: 110,
                        overflow: 'truncate'
                    },
                    axisTick: { show: false }
                },
                series: [
                    {
                        name: '通过',
                        type: 'bar',
                        stack: 'total',
                        barMaxWidth: 14,
                        emphasis: { focus: 'series' },
                        data: suiteStats.map(item => item.pass)
                    },
                    {
                        name: '失败',
                        type: 'bar',
                        stack: 'total',
                        barMaxWidth: 14,
                        emphasis: { focus: 'series' },
                        data: suiteStats.map(item => item.fail)
                    },
                    {
                        name: '错误',
                        type: 'bar',
                        stack: 'total',
                        barMaxWidth: 14,
                        emphasis: { focus: 'series' },
                        data: suiteStats.map(item => item.error)
                    },
                    {
                        name: '跳过',
                        type: 'bar',
                        stack: 'total',
                        barMaxWidth: 14,
                        emphasis: { focus: 'series' },
                        data: suiteStats.map(item => item.skip)
                    }
                ]
            };

            suiteChart.setOption(suiteOption);
            window.addEventListener('resize', function() {
                suiteChart.resize();
            });
        }

        // Responsive resize.
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }
    
    // Initialize chart when page is ready.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChart);
    } else {
        initChart();
    }
    </script>
    """  # variables: (Pass, fail, error)

    # ------------------------------------------------------------------------
    # Stylesheet
    #
    # alternatively use a <link> for external style sheet, e.g.
    #   <link rel="stylesheet" href="$url" type="text/css">

    STYLESHEET_TMPL = """
<style type="text/css">
:root {
        --primary-color: #1890ff;
        --success-color: #52c41a;
        --warning-color: #faad14;
        --danger-color: #f5222d;
        --info-color: #13c2c2;
        --border-color: #d9d9d9;
        --text-color: #262626;
    --text-secondary: #8c8c8c;
        --bg-color: #f0f2f5;
}

[data-bs-theme="dark"] {
        --primary-color: #177ddc;
        --success-color: #49aa19;
        --warning-color: #d89614;
        --danger-color: #d32029;
        --border-color: #434343;
        --text-color: #e8e8e8;
    --text-secondary: #a6a6a6;
        --bg-color: #141414;
}

    * {
        box-sizing: border-box;
    }

body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
        background: var(--bg-color);
    min-height: 100vh;
    padding: 24px;
    margin: 0;
        color: var(--text-color);
}

    .container-fluid {
        max-width: 1400px;
        margin: 0 auto;
    }

    /* Header */
    .header-card {
        background: white;
        border-radius: 8px;
    padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
        border: 1px solid var(--border-color);
    }

    [data-bs-theme="dark"] .header-card {
        background: #1f1f1f;
        border-color: var(--border-color);
}

.report-title {
        font-size: 24px;
        font-weight: 600;
        color: var(--text-color);
        margin-bottom: 16px;
    display: flex;
    align-items: center;
        gap: 8px;
}

.report-title i {
        color: var(--primary-color);
}

    /* Statistics */
.stats-grid {
    display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
        margin-bottom: 16px;
}

.stat-card {
        background: white;
        border-radius: 8px;
    padding: 20px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
        border: 1px solid var(--border-color);
        transition: all 0.2s;
    }

    [data-bs-theme="dark"] .stat-card {
        background: #1f1f1f;
        border-color: var(--border-color);
    }

.stat-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-color: var(--primary-color);
}

    .stat-card.info .stat-icon { color: var(--info-color); }
    .stat-card.primary .stat-icon { color: var(--primary-color); }
    .stat-card.success .stat-icon { color: var(--success-color); }
    .stat-card.secondary .stat-icon { color: var(--text-secondary); }

.stat-label {
    font-size: 14px;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.stat-value {
        font-size: 24px;
        font-weight: 600;
        color: var(--text-color);
}

.stat-icon {
        font-size: 20px;
        float: right;
        opacity: 0.8;
    }

    /* Chart */
    .chart-card {
        background: white;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
        border: 1px solid var(--border-color);
    }

    [data-bs-theme="dark"] .chart-card {
        background: #1f1f1f;
        border-color: var(--border-color);
    }

    /* Filters */
    .filter-buttons {
        margin-bottom: 0;
    }

    .filter-btn {
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 14px;
        transition: all 0.2s;
        background: white;
        color: var(--text-color);
    }

    [data-bs-theme="dark"] .filter-btn {
        background: #1f1f1f;
        border-color: var(--border-color);
}

    .filter-btn:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
    }

    .filter-btn.active {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: white;
    }

    /* Table */
.table-card {
        background: white;
        border-radius: 8px;
        padding: 24px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
        border: 1px solid var(--border-color);
    overflow: hidden;
}

    [data-bs-theme="dark"] .table-card {
        background: #1f1f1f;
        border-color: var(--border-color);
    }
    
    .table-card h2 {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-color);
    }

#result_table {
        width: 100%%;
        margin-bottom: 0;
        border-collapse: collapse;
}

#result_table thead th {
        background: #fafafa;
        color: var(--text-color);
    font-weight: 600;
        padding: 12px 16px;
    font-size: 14px;
        border-bottom: 1px solid var(--border-color);
    text-align: left;
    }

    [data-bs-theme="dark"] #result_table thead th {
        background: #141414;
}

#result_table tbody tr {
        transition: background 0.2s;
        border-bottom: 1px solid var(--border-color);
}

#result_table tbody tr:hover {
        background-color: #fafafa;
    }

    [data-bs-theme="dark"] #result_table tbody tr:hover {
        background-color: #262626;
}

#result_table td {
        padding: 12px 16px;
    vertical-align: middle;
    font-size: 14px;
}

    .passClass {
        background: #f6ffed;
    }

    [data-bs-theme="dark"] .passClass {
        background: rgba(82, 196, 26, 0.1);
    }

    .failClass {
        background: #fffbe6;
    }

    [data-bs-theme="dark"] .failClass {
        background: rgba(250, 173, 20, 0.1);
    }

    .errorClass {
        background: #fff1f0;
    }

    [data-bs-theme="dark"] .errorClass {
        background: rgba(245, 34, 45, 0.1);
    }

    .skipClass {
        background: #f0f5ff;
    }

    [data-bs-theme="dark"] .skipClass {
        background: rgba(24, 144, 255, 0.1);
    }

    #total_row {
        font-weight: 600;
        background: #fafafa;
        border-top: 2px solid var(--border-color);
    }

    [data-bs-theme="dark"] #total_row {
        background: #141414;
    }

    .passCase { color: var(--success-color); }
    .failCase { color: var(--warning-color); }
    .errorCase { color: var(--danger-color); }
    .skipCase { color: var(--primary-color); }

.testcase {
        margin-left: 24px;
    font-size: 14px;
    }

    /* Detail panel */
    .popup_link {
        display: inline-flex;
    align-items: center;
        gap: 4px;
        padding: 4px 12px;
        border-radius: 4px;
        text-decoration: none;
        font-size: 14px;
        transition: all 0.2s;
    }

    .popup_link:hover {
        opacity: 0.8;
    }

.popup_window {
    display: none;
    margin-top: 12px;
        background: #fafafa;
        border-radius: 6px;
        border: 1px solid var(--border-color);
        position: relative;
}

    [data-bs-theme="dark"] .popup_window {
        background: #141414;
        border-color: var(--border-color);
}

.popup_window_header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
        border-bottom: 1px solid var(--border-color);
}

    .popup_window_header strong {
        font-size: 14px;
        color: var(--text-color);
}

    .popup_window_actions {
        display: flex;
        gap: 8px;
    }

    .popup_window_actions button {
        background: white;
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 4px 12px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
        color: var(--text-color);
        display: flex;
    align-items: center;
        gap: 4px;
}

    [data-bs-theme="dark"] .popup_window_actions button {
        background: #1f1f1f;
    }

    .popup_window_actions button:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
}

    .popup_window_content {
        max-height: 400px;
        overflow-y: auto;
        padding: 16px;
    }

    .popup_window_content pre {
        white-space: pre-wrap;
        word-wrap: break-word;
        margin: 0;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.6;
        color: var(--text-color);
    }
    
    .copy-success {
        color: var(--success-color) !important;
        border-color: var(--success-color) !important;
    }

    /* Responsive */
@media (max-width: 768px) {
        body {
            padding: 16px;
        }

        .header-card, .chart-card, .table-card {
            padding: 16px;
        }

        .report-title {
            font-size: 20px;
        }

        .stats-grid {
            grid-template-columns: 1fr;
        }

        #result_table {
            font-size: 13px;
        }

        #result_table td, #result_table th {
            padding: 8px;
        }
    }

    /* Badges */
    .badge {
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 500;
        font-size: 12px;
        }

    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 4px;
            }

    [data-bs-theme="dark"] ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 0, 0, 0.3);
    }

    [data-bs-theme="dark"] ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
}

    /* Screenshots */
    .screenshot-section {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid var(--border-color);
    }

    .screenshot-header {
        font-weight: 600;
        font-size: 14px;
        color: var(--text-color);
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .screenshot-header-left {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .screenshot-view-toggle {
        display: flex;
        gap: 4px;
    }

    .screenshot-view-btn {
        padding: 2px 8px;
        font-size: 12px;
        border: 1px solid var(--border-color);
        background: white;
        color: var(--text-color);
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.2s;
    }

    [data-bs-theme="dark"] .screenshot-view-btn {
        background: #1f1f1f;
    }

    .screenshot-view-btn:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
    }

    .screenshot-view-btn.active {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: white;
    }

    /* Carousel view */
    .screenshot-carousel {
        position: relative;
        width: 100%;
        overflow: hidden;
        border-radius: 8px;
        background: #fafafa;
    }

    [data-bs-theme="dark"] .screenshot-carousel {
        background: #141414;
    }

    .screenshot-carousel-inner {
        display: flex;
        transition: transform 0.3s ease-in-out;
    }

    .screenshot-carousel-item {
        min-width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px;
    }

    .screenshot-carousel-item img {
        max-width: 100%;
        max-height: 500px;
        border-radius: 6px;
        border: 1px solid var(--border-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        cursor: pointer;
    }

    .screenshot-carousel-description {
        margin-top: 12px;
        font-size: 14px;
        color: var(--text-color);
        text-align: center;
    }

    .screenshot-carousel-control {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        width: 40px;
        height: 40px;
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(0,0,0,0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: #555;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10;
        opacity: 0;
        transition: all 0.3s;
    }

    .screenshot-carousel:hover .screenshot-carousel-control {
        opacity: 1;
    }

    .screenshot-carousel-control:hover {
        background: #fff;
        color: var(--primary-color);
        transform: translateY(-50%) scale(1.1);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }

    .screenshot-carousel-control.prev { left: 20px; }
    .screenshot-carousel-control.next { right: 20px; }

    .screenshot-carousel-indicators {
        display: flex;
        justify-content: center;
        gap: 8px;
        padding: 12px;
    }

    .screenshot-carousel-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--border-color);
        cursor: pointer;
        transition: all 0.2s;
    }

    .screenshot-carousel-indicator.active {
        background: var(--primary-color);
        width: 24px;
        border-radius: 4px;
    }

    /* Grid view */
    .screenshot-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 16px;
    }

    .screenshot-item {
        margin-bottom: 0;
    }

    .screenshot-description {
        font-size: 13px;
        color: #8c8c8c;
        margin-bottom: 8px;
        font-style: italic;
    }

    .screenshot-image {
        max-width: 100%;
        border-radius: 6px;
        border: 1px solid var(--border-color);
        cursor: pointer;
        transition: all 0.3s;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .screenshot-image:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    }

    /* Image preview modal */
    .image-modal {
        display: none;
        position: fixed;
        z-index: 9999;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        animation: fadeIn 0.3s;
    }

    .image-modal-content {
        margin: auto;
        display: block;
        max-width: 90%;
        max-height: 90%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        animation: zoomIn 0.3s;
    }

    .image-modal-caption {
        text-align: center;
        color: #fff;
        padding: 10px;
        position: absolute;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        font-size: 16px;
        background: rgba(0, 0, 0, 0.5);
        border-radius: 4px;
        padding: 8px 16px;
    }

    .image-modal-close {
        position: absolute;
        top: 30px;
        right: 30px;
        width: 50px;
        height: 50px;
        color: rgba(255, 255, 255, 0.8);
        font-size: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: transparent;
        cursor: pointer;
        transition: all 0.2s;
        z-index: 10002;
    }

    .image-modal-close:hover {
        background: transparent;
        color: #ff4d4f;
        transform: rotate(90deg);
    }

    .image-modal-nav {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        color: rgba(255, 255, 255, 0.7);
        font-size: 50px;
        font-weight: bold;
        cursor: pointer;
        padding: 0 20px;
        user-select: none;
        transition: all 0.3s;
        z-index: 10001;
        height: 100%;
        display: flex;
        align-items: center;
    }

    .image-modal-nav:hover {
        color: #fff;
        background: rgba(0, 0, 0, 0.2);
    }

    .image-modal-prev { left: 0; }
    .image-modal-next { right: 0; }

    .image-modal-counter {
        position: absolute;
        top: 20px;
        left: 20px;
        color: rgba(255, 255, 255, 0.9);
        font-size: 14px;
        background: rgba(0, 0, 0, 0.5);
        padding: 4px 10px;
        border-radius: 4px;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes zoomIn {
        from { transform: translate(-50%, -50%) scale(0.8); }
        to { transform: translate(-50%, -50%) scale(1); }
    }

    /* Clean fullscreen report workspace */
    :root {
        --app-bg: #f6f8fb;
        --panel-bg: #ffffff;
        --panel-soft: #f8fafc;
        --border: #e5e7eb;
        --text-main: #111827;
        --text-muted: #64748b;
        --primary: #4f46e5;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #3b82f6;
        --shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }

    [data-bs-theme="dark"] {
        --app-bg: #0f172a;
        --panel-bg: #111827;
        --panel-soft: #172033;
        --border: #273244;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --primary: #818cf8;
        --success: #34d399;
        --warning: #fbbf24;
        --danger: #fb7185;
        --info: #60a5fa;
    }

    html,
    body {
        width: 100%;
        height: 100%;
        margin: 0;
        overflow: hidden;
    }

    body {
        padding: 0;
        background: var(--app-bg);
        color: var(--text-main);
        font-family: "Inter Variable", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }

    .pt-main {
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        background: var(--app-bg);
    }

    .pt-content.container-fluid {
        max-width: none;
        height: 100vh;
        padding: 16px;
        display: grid;
        grid-template-columns: 500px minmax(0, 1fr);
        grid-template-rows: 48px minmax(190px, 22vh) minmax(0, 1fr);
        gap: 12px;
    }

    .header-card,
    .chart-card,
    .table-card {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--panel-bg) !important;
        box-shadow: var(--shadow) !important;
    }

    .page-header {
        grid-column: 1 / -1;
        grid-row: 1;
        min-height: 0;
        padding: 0 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: var(--panel-bg);
        box-shadow: var(--shadow);
    }

    .page-title {
        min-width: 0;
        margin: 0;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        color: var(--text-main);
        font-size: 18px;
        line-height: 1.2;
        font-weight: 850;
        letter-spacing: 0;
    }

    .page-title i {
        width: 30px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 9px;
        background: #eef2ff;
        color: var(--primary);
        font-size: 16px;
        flex: 0 0 auto;
    }

    [data-bs-theme="dark"] .page-title i {
        background: rgba(129, 140, 248, 0.16);
    }

    .header-card {
        grid-column: 1;
        grid-row: 2 / 4;
        height: 100%;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-height: 0;
        overflow: auto;
    }

    .report-title {
        margin: 0;
        padding-right: 52px;
        display: flex;
        align-items: center;
        gap: 12px;
        color: var(--text-main);
        font-size: 20px;
        line-height: 1.25;
        font-weight: 800;
        letter-spacing: 0;
    }

    .report-title i {
        width: 36px;
        height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: #eef2ff;
        color: var(--primary);
        font-size: 18px;
        flex: 0 0 auto;
    }

    [data-bs-theme="dark"] .report-title i {
        background: rgba(129, 140, 248, 0.16);
    }

    .overview-card {
        padding: 12px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--panel-soft);
    }

    .overview-title {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--text-main);
        font-size: 13px;
        font-weight: 800;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        margin: 0;
    }

    .meta-item {
        min-width: 0;
        min-height: 58px;
        padding: 10px;
        display: grid;
        grid-template-columns: 30px minmax(0, 1fr);
        align-items: center;
        gap: 8px;
        border: 1px solid var(--border);
        border-radius: 9px;
        background: var(--panel-bg);
    }

    .meta-icon {
        width: 30px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background: var(--panel-soft);
        color: var(--text-muted);
        font-size: 15px;
    }

    .meta-item.info .meta-icon { color: #06b6d4; }
    .meta-item.primary .meta-icon { color: var(--primary); }
    .meta-item.success .meta-icon { color: var(--success); }
    .meta-item.secondary .meta-icon { color: var(--text-muted); }

    .meta-body {
        min-width: 0;
    }

    .meta-label {
        display: block;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 700;
        line-height: 1.2;
    }

    .meta-value {
        display: block;
        margin-top: 5px;
        color: var(--text-main);
        font-size: 13px;
        line-height: 1.35;
        font-weight: 800;
        word-break: break-word;
    }

    .report-status-list {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
    }

    .report-status-pill {
        display: inline-flex;
        align-items: center;
        height: 20px;
        padding: 0 7px;
        border-radius: 999px;
        color: #fff;
        font-size: 10px;
        font-weight: 800;
        white-space: nowrap;
    }

    .report-status-pill.pass { background: var(--success); }
    .report-status-pill.fail { background: var(--warning); }
    .report-status-pill.error { background: var(--danger); }
    .report-status-pill.skip { background: var(--primary); }
    .report-status-pill.neutral { background: var(--text-muted); }

    .description-panel {
        padding: 10px;
        border: 1px solid var(--border);
        border-radius: 9px;
        background: var(--panel-bg);
    }

    .description-label {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 800;
    }

    .description {
        margin: 6px 0 0 !important;
        color: var(--text-main) !important;
        font-size: 13px !important;
        line-height: 1.5;
    }

    .chart-card {
        grid-column: 2;
        grid-row: 2;
        height: 100%;
        padding: 12px;
        min-height: 0;
        overflow: hidden;
        display: grid;
        grid-template-columns: minmax(320px, 35%) minmax(0, 1fr);
        gap: 12px;
    }

    .chart-panel {
        min-width: 0;
        min-height: 0;
        display: flex;
        flex-direction: column;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--panel-soft);
        overflow: hidden;
    }

    .chart-panel-title {
        flex: 0 0 auto;
        height: 34px;
        padding: 0 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: var(--text-main);
        font-size: 13px;
        font-weight: 800;
        border-bottom: 1px solid var(--border);
        background: var(--panel-bg);
    }

    .chart-panel-title span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .chart-canvas {
        flex: 1 1 auto;
        min-height: 0;
    }

    #chart,
    #suiteChart {
        width: 100% !important;
        height: 100% !important;
        min-height: 140px;
    }

    .table-card {
        grid-column: 2;
        grid-row: 3;
        height: 100%;
        min-height: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        overflow: visible;
    }

    .table-card > .d-flex {
        flex: 0 0 auto;
        min-height: 54px;
        margin: 0 !important;
        padding: 12px 16px;
        gap: 12px;
        flex-wrap: wrap;
        border-bottom: 1px solid var(--border);
        background: var(--panel-bg);
    }

    .table-card h2 {
        margin: 0;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: var(--text-main);
        font-size: 16px;
        font-weight: 800;
        letter-spacing: 0;
    }

    .filter-buttons {
        gap: 4px;
        padding: 4px;
        border: 0;
        border-radius: 10px;
        background: var(--panel-soft);
    }

    .filter-btn {
        height: 30px;
        padding: 0 14px;
        border: 0;
        border-radius: 8px !important;
        background: transparent;
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 700;
        transform: translateY(0);
        transition: background-color 160ms ease, color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }

    .filter-btn:hover {
        color: var(--primary);
        transform: translateY(-1px);
    }

    .filter-btn.active {
        background: var(--panel-bg);
        color: var(--primary);
        box-shadow: var(--shadow);
        transform: translateY(-1px);
    }

    .filter-btn.detail-active {
        background: var(--panel-bg);
        color: var(--primary);
        box-shadow: var(--shadow);
    }

    .table-responsive {
        flex: 1 1 auto;
        min-height: 0;
        overflow: auto;
        position: relative;
        padding: 0;
        background: var(--panel-bg);
    }

    #result_table {
        width: 100%;
        margin: 0;
        border-collapse: separate;
        border-spacing: 0;
        table-layout: fixed;
        --bs-table-bg: transparent;
        --bs-table-hover-bg: transparent;
        --bs-table-striped-bg: transparent;
        --bs-table-active-bg: transparent;
    }

    #result_table .case-name-col {
        width: 40%;
        min-width: 340px;
    }

    #result_table .metric-col {
        width: 92px;
    }

    #result_table .duration-col {
        width: 110px;
    }

    #result_table .action-col {
        width: 118px;
    }

    #result_table thead th {
        position: sticky;
        top: 0;
        z-index: 3;
        height: 44px;
        padding: 4px 14px 6px;
        border-top: 1px solid var(--border);
        border-bottom: 1px solid var(--border);
        background: var(--panel-soft);
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0;
        white-space: nowrap;
    }

    #result_table tbody tr {
        background: transparent !important;
    }

    #result_table tbody tr:hover {
        background: transparent !important;
    }

    #result_table tbody tr:hover td {
        background: transparent !important;
    }

    #result_table td {
        height: 48px;
        padding: 10px 14px;
        border-top: 0;
        border-bottom: 1px solid var(--border);
        background: var(--panel-bg) !important;
        color: var(--text-main);
        font-size: 13px;
        vertical-align: middle;
    }

    #result_table tbody tr td:first-child {
        border-left: 0;
        border-radius: 0;
    }

    #result_table tbody tr td:last-child {
        border-right: 0;
        border-radius: 0;
    }

    #result_table tbody tr:hover td {
        border-bottom-color: #cbd5e1;
        box-shadow: none;
    }

    .passClass,
    .failClass,
    .errorClass,
    .skipClass {
        background: transparent;
        border-left: 0;
        box-shadow: inset 4px 0 0 var(--success);
    }

    .failClass { box-shadow: inset 4px 0 0 var(--warning); }
    .errorClass { box-shadow: inset 4px 0 0 var(--danger); }
    .skipClass { box-shadow: inset 4px 0 0 var(--info); }

    .suite-name {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        font-size: 13px;
        font-weight: 850;
        color: var(--text-main);
    }

    .suite-name i {
        color: #334155;
    }

    [data-bs-theme="dark"] .suite-name i {
        color: var(--text-muted);
    }

    #total_row {
        background: transparent !important;
        font-weight: 800;
    }

    #total_row td {
        border-top: 1px solid var(--border);
        background: var(--panel-bg) !important;
    }

    .testcase {
        margin-left: 0;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--text-main);
        font-weight: 700;
    }

    .testcase i {
        color: var(--text-muted);
    }

    .badge {
        min-width: 30px;
        padding: 4px 8px;
        border-radius: 7px;
        font-size: 11px;
        font-weight: 800;
    }

    .duration-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 54px;
        padding: 3px 8px;
        border-radius: 999px;
        background: var(--panel-soft);
        color: var(--text-muted);
        border: 1px solid var(--border);
        font-size: 11px;
        font-weight: 800;
        white-space: nowrap;
    }

    .case-status-cell {
        display: flex;
        justify-content: center;
    }

    .case-status-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 56px;
        height: 26px;
        padding: 0 10px;
        border-radius: 8px;
        border: 1px solid var(--border);
        background: var(--panel-bg);
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 850;
        white-space: nowrap;
    }

    .case-status-pill.passCase {
        color: #047857;
        border-color: #bbf7d0;
        background: #f0fdf4;
    }

    .case-status-pill.failCase {
        color: #92400e;
        border-color: #fde68a;
        background: #fffbeb;
    }

    .case-status-pill.errorCase {
        color: #991b1b;
        border-color: #fecaca;
        background: #fef2f2;
    }

    .case-status-pill.skipCase {
        color: #1d4ed8;
        border-color: #bfdbfe;
        background: #eff6ff;
    }

    [data-bs-theme="dark"] .case-status-pill.passCase {
        color: #bbf7d0;
        border-color: rgba(16, 185, 129, 0.28);
        background: rgba(16, 185, 129, 0.12);
    }

    [data-bs-theme="dark"] .case-status-pill.failCase {
        color: #fde68a;
        border-color: rgba(245, 158, 11, 0.28);
        background: rgba(245, 158, 11, 0.12);
    }

    [data-bs-theme="dark"] .case-status-pill.errorCase {
        color: #fecaca;
        border-color: rgba(239, 68, 68, 0.28);
        background: rgba(239, 68, 68, 0.12);
    }

    [data-bs-theme="dark"] .case-status-pill.skipCase {
        color: #bfdbfe;
        border-color: rgba(59, 130, 246, 0.28);
        background: rgba(59, 130, 246, 0.12);
    }

    .case-empty-cell {
        color: transparent;
    }

    #result_table .btn-outline-primary,
    #result_table .btn-outline-info {
        min-width: 62px;
        border-color: #dbe4ff;
        background: #f8fbff;
        color: var(--primary);
    }

    #result_table .popup_link {
        border-color: var(--border);
        background: var(--panel-bg);
        color: var(--text-main);
    }

    #result_table .popup_link.failCase {
        color: #92400e;
        border-color: #fde68a;
        background: #fffbeb;
    }

    #result_table .popup_link.errorCase {
        color: #991b1b;
        border-color: #fecaca;
        background: #fef2f2;
    }

    #result_table .popup_link.skipCase {
        color: #1d4ed8;
        border-color: #bfdbfe;
        background: #eff6ff;
    }

    #result_table .btn-outline-primary:hover,
    #result_table .btn-outline-info:hover {
        border-color: var(--primary);
        background: #eef2ff;
        color: var(--primary);
    }

    #result_table .btn-outline-primary {
        height: 28px;
        padding: 0 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
    }

    [data-bs-theme="dark"] #result_table .btn-outline-primary,
    [data-bs-theme="dark"] #result_table .btn-outline-info {
        border-color: #334155;
        background: #172033;
        color: var(--primary);
    }

    .insights-card {
        grid-column: 1;
        grid-row: 1 / 3;
        min-height: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 10px;
        border: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        overflow: visible;
        order: 10;
    }

    .insight-panel {
        min-width: 0;
        min-height: 0;
        display: flex;
        flex-direction: column;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--panel-soft);
        overflow: hidden;
    }

    .header-card .insights-card {
        margin-top: 0;
    }

    .header-card .insight-panel {
        flex: 0 0 auto;
    }

    .header-card .insight-panel:nth-child(2) {
        flex: 0 0 auto;
        min-height: 0;
    }

    .insight-panel-title {
        flex: 0 0 auto;
        height: 38px;
        padding: 0 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border);
        background: var(--panel-bg);
        color: var(--text-main);
        font-size: 13px;
        font-weight: 800;
    }

    .insight-panel-title span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .insight-chart {
        flex: 1 1 auto;
        min-height: 0;
    }

    .coverage-metrics {
        flex: 1 1 auto;
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        padding: 10px;
    }

    .coverage-metric {
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 58px;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: var(--panel-bg);
    }

    .coverage-label {
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 700;
    }

    .coverage-value {
        margin-top: 6px;
        color: var(--text-main);
        font-size: 18px;
        font-weight: 900;
    }

    .failure-list {
        flex: 0 0 auto;
        min-height: 0;
        max-height: 320px;
        overflow: auto;
        padding: 10px;
        background: var(--panel-bg);
    }

    .failure-item {
        position: relative;
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: 10px;
        min-height: 54px;
        padding: 10px 12px;
        border: 1px solid var(--border);
        border-radius: 9px;
        background: var(--panel-bg);
        color: var(--text-main);
        box-shadow: 0 1px 1px rgba(15, 23, 42, 0.03);
    }

    .failure-item + .failure-item {
        margin-top: 8px;
    }

    .failure-item:hover {
        border-color: #cbd5e1;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06);
    }

    [data-bs-theme="dark"] .failure-item:hover {
        border-color: #475569;
    }

    .failure-status {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 42px;
        height: 24px;
        padding: 0 8px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 900;
        white-space: nowrap;
    }

    .failure-status.failure {
        color: #92400e;
        background: #fef3c7;
        border: 1px solid #fde68a;
    }

    .failure-status.error {
        color: #991b1b;
        background: #fee2e2;
        border: 1px solid #fecaca;
    }

    [data-bs-theme="dark"] .failure-status.failure {
        color: #fde68a;
        background: rgba(245, 158, 11, 0.14);
        border-color: rgba(245, 158, 11, 0.28);
    }

    [data-bs-theme="dark"] .failure-status.error {
        color: #fecaca;
        background: rgba(239, 68, 68, 0.14);
        border-color: rgba(239, 68, 68, 0.28);
    }

    .failure-name {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 13px;
        font-weight: 850;
    }

    .failure-suite {
        margin-top: 3px;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 700;
    }

    .failure-empty {
        height: 100%;
        min-height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 800;
    }

    .btn,
    .popup_link,
    .popup_window_actions button,
    .screenshot-view-btn {
        border-radius: 8px !important;
        font-size: 12px;
        font-weight: 700;
    }

    .popup_window {
        display: block;
        margin: 8px 18px 6px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--panel-bg);
        box-shadow: none;
    }

    #result_table .popup_window {
        position: static;
        width: auto;
        max-width: calc(100% - 36px);
        text-align: left;
    }

    #result_table .detail-row td {
        height: auto;
        padding: 0 8px 8px;
        border-bottom: 1px solid var(--border);
        background: var(--panel-soft) !important;
    }

    .popup_window_header {
        min-height: 32px;
        padding: 6px 8px 6px 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        border-bottom: 1px solid var(--border);
        background: var(--panel-soft);
        border-radius: 8px 8px 0 0;
    }

    .popup_window_header strong {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: var(--text-main);
    }

    .popup_window_actions {
        display: flex;
        align-items: center;
        gap: 6px;
        flex: 0 0 auto;
        margin-left: auto;
    }

    .popup_window_actions button {
        height: 26px;
        padding: 0 9px;
        border-color: var(--border);
        background: var(--panel-bg);
        color: var(--text-muted);
    }

    .popup_window_content {
        max-height: min(48vh, 520px);
        overflow: auto;
        padding: 8px 10px 10px;
    }

    .popup_window_content pre {
        margin: 0;
        padding: 8px 10px;
        border: 1px solid var(--border);
        border-radius: 7px;
        background: var(--panel-soft);
        color: var(--text-main);
        font-size: 11px;
        line-height: 1.4;
        white-space: pre-wrap;
    }

    .screenshot-container {
        margin-top: 8px !important;
    }

    .screenshot-container > .d-flex {
        margin-bottom: 6px !important;
    }

    .screenshot-carousel,
    .screenshot-item {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--panel-soft);
    }

    .table-toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .page-actions {
        flex: 0 0 auto;
    }

    .report-tool-btn {
        height: 30px;
        padding: 0 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--panel-bg);
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 750;
        white-space: nowrap;
        transition: background-color 160ms ease, color 160ms ease, border-color 160ms ease, transform 160ms ease;
    }

    .report-tool-btn:hover,
    .report-tool-btn.active {
        color: var(--primary);
        border-color: #c7d2fe;
        background: #eef2ff;
        transform: translateY(-1px);
    }

    [data-bs-theme="dark"] .report-tool-btn:hover,
    [data-bs-theme="dark"] .report-tool-btn.active {
        background: rgba(129, 140, 248, 0.14);
    }

    @media (max-width: 1080px) {
        .pt-main {
            overflow: auto;
        }

        .pt-content.container-fluid {
            min-height: 100vh;
            height: auto;
            grid-template-columns: 1fr;
            grid-template-rows: auto auto 280px minmax(620px, 1fr);
        }

        .page-header { grid-column: 1; grid-row: 1; }
        .header-card { grid-column: 1; grid-row: 2; }
        .chart-card {
            grid-column: 1;
            grid-row: 3;
            grid-template-columns: 1fr;
        }
        .header-card .insight-panel:nth-child(2) {
            min-height: 120px;
        }
        .table-card { grid-column: 1; grid-row: 4; }
    }

    @media (max-width: 720px) {
        .pt-content.container-fluid {
            padding: 10px;
            gap: 10px;
        }

        .header-card {
            padding: 14px;
        }

        .report-title {
            font-size: 18px;
        }

        .stats-grid {
            grid-template-columns: 1fr;
        }

        .filter-buttons {
            width: 100%;
        }

        .filter-btn {
            flex: 1 1 0;
            padding: 0 8px;
        }
    }

    @media print {
        html,
        body,
        .pt-main {
            height: auto;
            overflow: visible;
            background: #fff;
        }

        .pt-content.container-fluid {
            height: auto;
            display: block;
            padding: 0;
        }

        .table-toolbar,
        .filter-buttons,
        .popup_window_actions {
            display: none !important;
        }

        .header-card,
        .chart-card,
        .table-card {
            margin-bottom: 12px;
            break-inside: avoid;
        }

        .table-responsive {
            overflow: visible;
        }
    }
</style>
"""

    # ------------------------------------------------------------------------
    # Heading
    #

    HEADING_TMPL = """
    <div class="page-header">
        <h1 class="page-title">
            <i class="bi bi-clipboard-check"></i>
            %(title)s
        </h1>
        <div class="table-toolbar page-actions">
            <button type="button" class="report-tool-btn" onclick="toggleTheme()" title="切换主题">
                <i class="bi bi-moon-stars-fill" id="theme-icon"></i>
                <span>主题</span>
            </button>
            <button type="button" class="report-tool-btn" onclick="savePageScreenshot()" title="保存当前页面截图">
                <i class="bi bi-camera"></i>
                <span>截图</span>
            </button>
            <button type="button" class="report-tool-btn" onclick="exportPdf()" title="通过浏览器打印导出 PDF">
                <i class="bi bi-file-earmark-pdf"></i>
                <span>PDF</span>
            </button>
        </div>
    </div>

    <!-- Header -->
    <div class='header-card el-card'>
        <div class="overview-card">
            <div class="overview-title">
                <i class="bi bi-info-circle"></i> 报告概览
            </div>
            <div class='stats-grid'>
                %(parameters)s
            </div>
            <div class="description-panel">
                <div class="description-label">
                    <i class="bi bi-card-text"></i> 描述
                </div>
                <p class='description text-muted'>%(description)s</p>
            </div>
        </div>
        %(insights)s
</div>

    <!-- Chart -->
    <div class='chart-card el-card'>
        <div class="chart-panel chart-panel-summary">
            <div class="chart-panel-title">
                <span><i class="bi bi-pie-chart"></i> 执行情况</span>
            </div>
            <div id="chart" class="chart-canvas"></div>
        </div>
        <div class="chart-panel chart-panel-suite">
            <div class="chart-panel-title">
                <span><i class="bi bi-bar-chart"></i> 套件分布</span>
            </div>
            <div id="suiteChart" class="chart-canvas"></div>
        </div>
    </div>
    
    <script>
    // Update theme icon
    function updateThemeIcon() {
        const icon = document.getElementById('theme-icon');
        const theme = document.documentElement.getAttribute('data-bs-theme');
        icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
    
    document.addEventListener('DOMContentLoaded', updateThemeIcon);
    
    // Update the icon after toggling the theme.
    const originalToggleTheme = window.toggleTheme;
    window.toggleTheme = function() {
        originalToggleTheme();
        updateThemeIcon();
    };
    </script>
"""  # variables: (title, parameters, description, insights)

    INSIGHTS_TMPL = """
    <div class="insights-card el-card">
        <div class="insight-panel">
            <div class="insight-panel-title">
                <span><i class="bi bi-camera"></i> 覆盖统计</span>
            </div>
            <div class="coverage-metrics">
                <div class="coverage-metric">
                    <div class="coverage-label">截图总数</div>
                    <div class="coverage-value">%(screenshot_count)s</div>
                </div>
                <div class="coverage-metric">
                    <div class="coverage-label">有截图用例</div>
                    <div class="coverage-value">%(screenshot_case_count)s</div>
                </div>
                <div class="coverage-metric">
                    <div class="coverage-label">有输出用例</div>
                    <div class="coverage-value">%(output_case_count)s</div>
                </div>
                <div class="coverage-metric">
                    <div class="coverage-label">平均耗时</div>
                    <div class="coverage-value">%(avg_duration)s</div>
                </div>
            </div>
        </div>
        <div class="insight-panel">
            <div class="insight-panel-title">
                <span><i class="bi bi-bug"></i> 失败/错误用例</span>
            </div>
            <div class="failure-list">
                %(failure_items)s
            </div>
        </div>
    </div>
"""  # variables: (screenshot_count, screenshot_case_count, output_case_count, avg_duration, failure_items)

    FAILURE_ITEM_TMPL = """
                <div class="failure-item %(status_class)s">
                    <div>
                        <div class="failure-name" title="%(name)s">%(name)s</div>
                        <div class="failure-suite">%(suite)s</div>
                    </div>
                    %(badge)s
                </div>
"""

    HEADING_ATTRIBUTE_TMPL = """
            <div class='meta-item %(card_class)s'>
                <i class='%(icon)s meta-icon'></i>
                <div class="meta-body">
                    <span class='meta-label'>%(name)s</span>
                    <span class='meta-value'>%(value)s</span>
                </div>
            </div>
"""  # variables: (name, value, card_class, icon)

    # ------------------------------------------------------------------------
    # Report
    #

    REPORT_TMPL = u"""
    <div class="table-card el-card">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="mb-0">
                <i class="bi bi-list-check"></i> 测试详情
        </h2>
            <div class="table-toolbar">
                <div class="filter-buttons btn-group" role="group">
                    <button type="button" class="filter-btn active" onclick='showCase(0)'>
                    <i class="bi bi-clipboard-data"></i> 总结
                    </button>
                    <button type="button" class="filter-btn" onclick='showCase(1)'>
                    <i class="bi bi-exclamation-triangle"></i> 失败
                    </button>
                    <button type="button" class="filter-btn" onclick='showCase(2)'>
                    <i class="bi bi-list-ul"></i> 全部
                    </button>
                    <button type="button" class="filter-btn" onclick="toggleAllDetails(this)" title="展开或收起所有详情">
                    <i class="bi bi-arrows-expand"></i> <span class="tool-label">展开详情</span>
                    </button>
                </div>
        </div>
    </div>
    
    <div class="table-responsive">
            <table id='result_table' class="table align-middle">
            <thead>
                <tr>
                        <th class="case-name-col">测试套件/测试用例</th>
                        <th class="metric-col text-center">总数</th>
                        <th class="metric-col text-center">通过</th>
                        <th class="metric-col text-center">失败</th>
                        <th class="metric-col text-center">错误</th>
                        <th class="metric-col text-center">跳过</th>
                        <th class="duration-col text-center">耗时</th>
                        <th class="action-col text-center">查看</th>
                </tr>
            </thead>
            <tbody>
                %(test_list)s
                    <tr id='total_row'>
                        <td><span class="suite-name"><i class="bi bi-calculator"></i> 总计</span></td>
    <td class="text-center"><strong>%(count)s</strong></td>
                        <td class="text-center"><span class="badge bg-success">%(Pass)s</span></td>
    <td class="text-center"><span class="badge bg-warning">%(fail)s</span></td>
    <td class="text-center"><span class="badge bg-danger">%(error)s</span></td>
    <td class="text-center"><span class="badge bg-primary">%(skip)s</span></td>
    <td class="text-center">&nbsp;</td>
    <td>&nbsp;</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
"""  # variables: (test_list, count, Pass, fail, error, skip)

    REPORT_CLASS_TMPL = u"""
    <tr class='%(style)s'>
        <td>
            <span class="suite-name"><i class="bi bi-folder-fill"></i> %(desc)s</span>
        </td>
    <td class="text-center">%(count)s</td>
        <td class="text-center"><span class="badge bg-success">%(Pass)s</span></td>
    <td class="text-center"><span class="badge bg-warning">%(fail)s</span></td>
    <td class="text-center"><span class="badge bg-danger">%(error)s</span></td>
    <td class="text-center"><span class="badge bg-primary">%(skip)s</span></td>
    <td class="text-center"><span class="duration-pill">%(duration)s</span></td>
    <td class="text-center">
            <a href="javascript:showClassDetail('%(cid)s',%(count)s)" class="btn btn-sm btn-outline-primary">
                <i class="bi bi-chevron-down"></i> 详情
            </a>
    </td>
    </tr>
"""  # variables: (style, desc, count, Pass, fail, error, skip, cid)

    REPORT_TEST_WITH_OUTPUT_TMPL = r"""
<tr id='%(tid)s' style='display:none;'>
    <td class='%(style)s'>
        <div class='testcase'>
            <i class="bi bi-file-earmark-code"></i> %(desc)s
        </div>
    </td>
    <td class="text-center case-empty-cell">&nbsp;</td>
    <td class="text-center">%(pass_cell)s</td>
    <td class="text-center">%(fail_cell)s</td>
    <td class="text-center">%(error_cell)s</td>
    <td class="text-center">%(skip_cell)s</td>
    <td class="text-center"><span class="duration-pill">%(duration)s</span></td>
    <td class="text-center">
        <a class="popup_link %(status_class)s btn btn-sm btn-outline-info" onfocus='this.blur();' href="javascript:showTestDetail('div_%(tid)s')">
            <i class="bi bi-info-circle"></i> 详情
        </a>
    </td>
</tr>
<tr id='div_%(tid)s' class="detail-row" style='display:none;'>
    <td colspan="8">
        <div class="popup_window">
            <div class="popup_window_header">
                <strong><i class="bi bi-terminal"></i> 执行详情</strong>
                <div class="popup_window_actions">
                    <button onclick="copyTestDetail('content_%(tid)s', this)" title="复制内容">
                        <i class="bi bi-clipboard"></i> 复制
                    </button>
                    <button onclick="showTestDetail('div_%(tid)s')" title="关闭">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            </div>
            <div class="popup_window_content">
                <pre id='content_%(tid)s'>%(script)s</pre>
                %(screenshots)s
            </div>
        </div>
    </td>
</tr>
"""  # variables: (tid, Class, style, desc, status, status cells, screenshots)

    REPORT_TEST_OUTPUT_TMPL = r"""%(id)s: %(output)s"""  # variables: (id, output)

    SCREENSHOT_TMPL = """
    <div class="screenshot-container" id="screenshot-%(tid)s">
        <div class="d-flex justify-content-between align-items-center">
            <h6 class="mb-0"><i class="bi bi-card-image"></i> 截图 (%(count)s)</h6>
            <div class="screenshot-view-toggle" style="%(toggle_style)s">
                <button class="btn btn-sm btn-outline-secondary screenshot-view-btn %(btn_carousel_active)s" onclick="switchScreenshotView('%(tid)s', 'carousel')" title="轮播视图">
                    <i class="bi bi-collection-play"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary screenshot-view-btn %(btn_grid_active)s" onclick="switchScreenshotView('%(tid)s', 'grid')" title="网格视图">
                    <i class="bi bi-grid-3x3-gap"></i>
                </button>
            </div>
        </div>
        
        <!-- Carousel view -->
        <div class="screenshot-carousel" id="carousel-%(tid)s" style="%(carousel_style)s">
            <div class="screenshot-carousel-inner" id="carousel-inner-%(tid)s">
                %(carousel_items)s
            </div>
            <button class="screenshot-carousel-control prev" onclick="moveCarousel('%(tid)s', -1)">
                <i class="bi bi-chevron-left"></i>
            </button>
            <button class="screenshot-carousel-control next" onclick="moveCarousel('%(tid)s', 1)">
                <i class="bi bi-chevron-right"></i>
            </button>
            <div class="screenshot-carousel-indicators" id="indicators-%(tid)s">
                %(indicators)s
            </div>
        </div>
        
        <!-- Grid view -->
        <div class="screenshot-grid" id="grid-%(tid)s" style="%(grid_style)s">
            %(grid_items)s
        </div>
    </div>
    """

    SCREENSHOT_CAROUSEL_ITEM_TMPL = """
<div class="screenshot-carousel-item">
    <img src="data:image/png;base64,%(data)s" 
         alt="%(description)s"
         onclick="openImageModal('%(tid)s', %(index)s)">
    <div class="screenshot-carousel-description">%(description)s</div>
</div>
"""

    SCREENSHOT_GRID_ITEM_TMPL = """
<div class="screenshot-item">
    <div class="screenshot-description">%(description)s</div>
    <img src="data:image/png;base64,%(data)s" 
         alt="%(description)s" 
         class="screenshot-image"
         onclick="openImageModal('%(tid)s', %(index)s)">
</div>
"""

    # ------------------------------------------------------------------------
    # Page scripts
    #

    ENDING_TMPL = """
<script>
    // Image preview modal with carousel support.
    let currentModalImages = [];
    let currentModalIndex = 0;

    function openImageModal(tid, index) {
        // Collect all screenshots for this case.
        const gridContainer = document.getElementById('grid-' + tid);
        if (!gridContainer) return;
        
        const imgs = gridContainer.querySelectorAll('img');
        currentModalImages = Array.from(imgs).map(img => ({
            src: img.src,
            description: img.getAttribute('alt') || ''
        }));
        currentModalIndex = index;
        
        let modal = document.getElementById('imageModal');
        if (!modal) {
            // Create modal DOM.
            const modalHtml = `
                <div id="imageModal" class="image-modal">
                    <div class="image-modal-close" onclick="closeImageModal()">
                        <i class="bi bi-x-lg"></i>
                    </div>
                    <div class="image-modal-nav image-modal-prev" onclick="changeModalImage(-1)">
                        <i class="bi bi-chevron-left"></i>
                    </div>
                    <div class="image-modal-nav image-modal-next" onclick="changeModalImage(1)">
                        <i class="bi bi-chevron-right"></i>
                    </div>
                    <div class="image-modal-counter" id="modalCounter"></div>
                    <img class="image-modal-content" id="modalImage">
                    <div class="image-modal-caption" id="modalCaption"></div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modal = document.getElementById('imageModal');
            
            // Click backdrop to close.
            modal.addEventListener('click', function(e) {
                if (e.target === modal) closeImageModal();
            });
        }
        
        updateModalContent();
        modal.style.display = 'block';
    }

    function updateModalContent() {
        if (!currentModalImages.length) return;
        
        const data = currentModalImages[currentModalIndex];
        const img = document.getElementById('modalImage');
        const caption = document.getElementById('modalCaption');
        const counter = document.getElementById('modalCounter');
        
        img.src = data.src;
        caption.textContent = data.description;
        counter.textContent = `${currentModalIndex + 1} / ${currentModalImages.length}`;
    }

    function changeModalImage(direction) {
        currentModalIndex += direction;
        if (currentModalIndex < 0) {
            currentModalIndex = currentModalImages.length - 1;
        } else if (currentModalIndex >= currentModalImages.length) {
            currentModalIndex = 0;
        }
        updateModalContent();
    }

    function closeImageModal() {
        const modal = document.getElementById('imageModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Keyboard shortcuts: ESC closes, arrow keys switch images.
    document.addEventListener('keydown', function(event) {
        const modal = document.getElementById('imageModal');
        if (modal && modal.style.display === 'block') {
            if (event.key === 'Escape') {
                closeImageModal();
            } else if (event.key === 'ArrowLeft') {
                changeModalImage(-1);
            } else if (event.key === 'ArrowRight') {
                changeModalImage(1);
            }
        }
    });

    // Screenshot carousel state.
    const carouselStates = {};

    function switchScreenshotView(tid, view) {
        const carousel = document.getElementById('carousel-' + tid);
        const grid = document.getElementById('grid-' + tid);
        const section = document.getElementById('screenshot-' + tid);
        const buttons = section.querySelectorAll('.screenshot-view-btn');
        
        buttons.forEach(btn => btn.classList.remove('active'));
        
        if (view === 'carousel') {
            carousel.style.display = 'block';
            grid.style.display = 'none';
            buttons[0].classList.add('active');
        } else {
            carousel.style.display = 'none';
            grid.style.display = 'grid';
            buttons[1].classList.add('active');
        }
    }

    function moveCarousel(tid, direction) {
        if (!carouselStates[tid]) {
            carouselStates[tid] = 0;
        }
        
        const inner = document.getElementById('carousel-inner-' + tid);
        const items = inner.children;
        const totalItems = items.length;
        
        carouselStates[tid] += direction;
        
        if (carouselStates[tid] < 0) {
            carouselStates[tid] = totalItems - 1;
        } else if (carouselStates[tid] >= totalItems) {
            carouselStates[tid] = 0;
        }
        
        updateCarousel(tid);
    }

    function goToSlide(tid, index) {
        carouselStates[tid] = index;
        updateCarousel(tid);
    }

    function updateCarousel(tid) {
        const inner = document.getElementById('carousel-inner-' + tid);
        const indicatorsContainer = document.getElementById('indicators-' + tid);
        const indicators = indicatorsContainer.querySelectorAll('.screenshot-carousel-indicator');
        const currentIndex = carouselStates[tid] || 0;
        
        inner.style.transform = `translateX(-${currentIndex * 100}%)`;
        
        indicators.forEach((indicator, index) => {
            if (index === currentIndex) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        });
    }

    // Initialize all screenshot carousels.
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.screenshot-carousel').forEach(carousel => {
            const tid = carousel.id.replace('carousel-', '');
            if (!carouselStates[tid]) {
                carouselStates[tid] = 0;
            }
        });
    });
    </script>
    """

# -------------------- The end of the Template class -------------------


TestResult = unittest.TestResult


class _TestResult(TestResult):
    # note: _TestResult is a pure representation of results.
    # It lacks the output and reporting ability compares to unittest._TextTestResult.
    
    def __init__(self, verbosity=1):
        TestResult.__init__(self)
        self.stdout0 = None
        self.stderr0 = None
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        self.skip_count = 0
        self.verbosity = verbosity

        # result is a list of result in 4 tuple
        # (
        #   result code (0: success; 1: fail; 2: error; 3: skip),
        #   TestCase object,
        #   Test output (byte string),
        #   stack trace,
        #   screenshots,
        # )
        self.result = []
        self.subtestlist = []
        self.outputBuffer = io.StringIO()
        self.test_start_time = round(time.time(), 2)
        self.current_test_start_time = None
        self.current_screenshots = []

    def startTest(self, test):
        global _current_result
        _current_result = self
        TestResult.startTest(self, test)
        self.current_screenshots = []
        self.current_test_start_time = time.time()
        # just one buffer for both stdout and stderr
        self.outputBuffer = io.StringIO()
        stdout_redirector.fp = self.outputBuffer
        stderr_redirector.fp = self.outputBuffer
        self.stdout0 = sys.stdout
        self.stderr0 = sys.stderr
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector

    def _elapsed(self):
        if self.current_test_start_time is None:
            return 0.0
        return round(time.time() - self.current_test_start_time, 4)

    def attach_screenshot(self, image_source, description=""):
        # Attach a screenshot to the current test.
        screenshot = ScreenshotManager.to_base64(image_source, description)
        if screenshot:
            self.current_screenshots.append(screenshot)

    def complete_output(self):
        # Disconnect output redirection and return buffer. Safe to call multiple times.
        if self.stdout0:
            sys.stdout = self.stdout0
            sys.stderr = self.stderr0
            self.stdout0 = None
            self.stderr0 = None
        return self.outputBuffer.getvalue()

    def stopTest(self, test):
        global _current_result
        # Usually one of addSuccess, addError or addFailure would have been called.
        # But there are some path in unittest that would bypass this.
        # We must disconnect stdout in stopTest(), which is guaranteed to be called.
        self.complete_output()
        if _current_result is self:
            _current_result = None

    def addSuccess(self, test):
        if test not in self.subtestlist:
            self.success_count += 1
            TestResult.addSuccess(self, test)
            output = self.complete_output()
            self.result.append((0, test, output, '', self.current_screenshots[:], self._elapsed()))
            if self.verbosity > 1:
                sys.stderr.write('ok ')
                sys.stderr.write(str(test))
                sys.stderr.write('\n')
            else:
                sys.stderr.write('S  ')

    def addError(self, test, err):
        self.error_count += 1
        TestResult.addError(self, test, err)
        _, _exc_str = self.errors[-1]
        output = self.complete_output()
        self.result.append((2, test, output, _exc_str, self.current_screenshots[:], self._elapsed()))
        if self.verbosity > 1:
            sys.stderr.write('E  ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('E')

    def addFailure(self, test, err):
        self.failure_count += 1
        TestResult.addFailure(self, test, err)
        _, _exc_str = self.failures[-1]
        output = self.complete_output()
        self.result.append((1, test, output, _exc_str, self.current_screenshots[:], self._elapsed()))
        if self.verbosity > 1:
            sys.stderr.write('F  ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('F')

    def addSkip(self, test, reason):
        self.skip_count += 1
        TestResult.addSkip(self, test, reason)
        output = self.complete_output()
        self.result.append((3, test, output, 'Skipped: ' + reason, self.current_screenshots[:], self._elapsed()))
        if self.verbosity > 1:
            sys.stderr.write('SKIP ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('s')

    def addSubTest(self, test, subtest, err):
        if err is not None:
            if getattr(self, 'failfast', False):
                self.stop()
            if issubclass(err[0], test.failureException):
                self.failure_count += 1
                errors = self.failures
                errors.append((subtest, self._exc_info_to_string(err, subtest)))
                output = self.complete_output()
                self.result.append((1, test, output + '\nSubTestCase Failed:\n' + str(subtest),
                                    self._exc_info_to_string(err, subtest), self.current_screenshots[:], self._elapsed()))
                if self.verbosity > 1:
                    sys.stderr.write('F  ')
                    sys.stderr.write(str(subtest))
                    sys.stderr.write('\n')
                else:
                    sys.stderr.write('F')
            else:
                self.error_count += 1
                errors = self.errors
                errors.append((subtest, self._exc_info_to_string(err, subtest)))
                output = self.complete_output()
                self.result.append(
                    (2, test, output + '\nSubTestCase Error:\n' + str(subtest), self._exc_info_to_string(err, subtest), self.current_screenshots[:], self._elapsed()))
                if self.verbosity > 1:
                    sys.stderr.write('E  ')
                    sys.stderr.write(str(subtest))
                    sys.stderr.write('\n')
                else:
                    sys.stderr.write('E')
            self._mirrorOutput = True
        else:
            self.subtestlist.append(subtest)
            self.subtestlist.append(test)
            self.success_count += 1
            output = self.complete_output()
            self.result.append((0, test, output + '\nSubTestCase Pass:\n' + str(subtest), '', self.current_screenshots[:], self._elapsed()))
            if self.verbosity > 1:
                sys.stderr.write('ok ')
                sys.stderr.write(str(subtest))
                sys.stderr.write('\n')
            else:
                sys.stderr.write('S')


class UhtmlLit(Template_mixin):

    def __init__(self, stream=sys.stdout, verbosity=1, title=None, description=None, tester=None, open_in_browser=False):
        self.stream = stream
        self.verbosity = verbosity
        self.open_in_browser = open_in_browser
        if title is None:
            self.title = self.DEFAULT_TITLE
        else:
            self.title = title
        if description is None:
            self.description = self.DEFAULT_DESCRIPTION
        else:
            self.description = description
        if tester is None:
            self.tester = "QA Team"
        else:
            self.tester = tester

        self.startTime = datetime.datetime.now()
        
    def run(self, test):
        "Run the given test case or test suite."
        global _current_result
        result = _TestResult(self.verbosity)
        _current_result = result
        try:
            test(result)
        finally:
            _current_result = None
        self.stopTime = datetime.datetime.now()
        self.generateReport(test, result)
        print('\nTime 运行时长: %s' % (self.stopTime-self.startTime), file=sys.stderr)
        
        # Open the report automatically when requested.
        if self.open_in_browser and hasattr(self.stream, 'name'):
            report_path = os.path.abspath(self.stream.name)
            webbrowser.open('file://' + report_path)
            print('报告已在浏览器中打开: %s' % report_path, file=sys.stderr)
        
        return result

    def sortResult(self, result_list):
        # unittest does not seems to run in any particular order.
        # Here at least we want to group them together by class.
        rmap = {}
        classes = []
        for n,t,o,e,*extra in result_list:
            cls = t.__class__
            if cls not in rmap:
                rmap[cls] = []
                classes.append(cls)
            screenshots = extra[0] if extra else []
            duration = extra[1] if len(extra) > 1 else 0.0
            rmap[cls].append((n,t,o,e,screenshots,duration))
        r = [(cls, rmap[cls]) for cls in classes]
        return r

    def getReportAttributes(self, result):
        # Return report attributes as a list of (name, value).
        # Override this to add custom attributes.
        startTime = str(self.startTime)[:19]
        duration = self._format_duration((self.stopTime - self.startTime).total_seconds())
        status = []
        if result.success_count:
            status.append('<span class="report-status-pill pass">通过 %s</span>' % result.success_count)
        if result.failure_count:
            status.append('<span class="report-status-pill fail">失败 %s</span>' % result.failure_count)
        if result.error_count:
            status.append('<span class="report-status-pill error">错误 %s</span>' % result.error_count)
        if result.skip_count:
            status.append('<span class="report-status-pill skip">跳过 %s</span>' % result.skip_count)
        if status:
            status = '<span class="report-status-list">%s</span>' % ''.join(status)
        else:
            status = '<span class="report-status-pill neutral">无结果</span>'
        return [
            ('开始时间', startTime),
            ('运行时长', duration),
            ('状态', status),
            ('测试人员', self.tester),
        ]

    def generateReport(self, test, result):
        report_attrs = self.getReportAttributes(result)
        generator = 'UhtmlLit %s' % __version__
        stylesheet = self._generate_stylesheet()
        insights = self._generate_insights(result)
        heading = self._generate_heading(report_attrs, insights)
        report = self._generate_report(result)
        ending = self._generate_ending()
        chart = self._generate_chart(result)
        output = self.HTML_TMPL % dict(
            title = saxutils.escape(self.title),
            generator = generator,
            stylesheet = stylesheet,
            heading = heading,
            report = report,
            ending = ending,
            chart_script = chart
        )
        self.stream.write(output.encode('utf8'))

    def _generate_stylesheet(self):
        return self.STYLESHEET_TMPL

    def _generate_heading(self, report_attrs, insights):
        a_lines = []
        # Icon and color mapping for report attributes.
        attr_config = {
            '开始时间': {'icon': 'bi bi-clock-history', 'class': 'info'},
            '运行时长': {'icon': 'bi bi-stopwatch', 'class': 'primary'},
            '状态': {'icon': 'bi bi-flag-fill', 'class': 'success'},
            '测试人员': {'icon': 'bi bi-person-fill', 'class': 'secondary'},
        }
        
        for name, value in report_attrs:
            config = attr_config.get(name, {'icon': 'bi bi-info-circle', 'class': 'info'})
            value_html = value if name == '状态' else saxutils.escape(value)
            line = self.HEADING_ATTRIBUTE_TMPL % dict(
                name = saxutils.escape(name),
                value = value_html,
                card_class = config['class'],
                icon = config['icon'],
            )
            a_lines.append(line)
        heading = self.HEADING_TMPL % dict(
            title = saxutils.escape(self.title),
            parameters = ''.join(a_lines),
            description = saxutils.escape(self.description),
            insights = insights,
        )
        return heading

    def _collect_case_metrics(self, result):
        cases = []
        sortedResult = self.sortResult(result.result)
        for cls, cls_results in sortedResult:
            if cls.__module__ == "__main__":
                suite_name = cls.__name__
            else:
                suite_name = "%s.%s" % (cls.__module__, cls.__name__)

            for n, test, output, error, *extra in cls_results:
                screenshots = extra[0] if extra else []
                duration = extra[1] if len(extra) > 1 else 0.0
                test_name = test.id().split('.')[-1]
                desc = test.shortDescription()
                if desc:
                    test_name = '%s: %s' % (test_name, desc)
                cases.append({
                    'status': n,
                    'suite': suite_name,
                    'name': test_name,
                    'output': output,
                    'error': error,
                    'screenshots': screenshots,
                    'duration': float(duration or 0),
                })
        return cases

    def _generate_insights(self, result):
        cases = self._collect_case_metrics(result)
        screenshot_count = sum(len(case['screenshots']) for case in cases)
        screenshot_case_count = sum(1 for case in cases if case['screenshots'])
        output_case_count = sum(1 for case in cases if case['output'] or case['error'])
        avg_duration = (sum(case['duration'] for case in cases) / len(cases)) if cases else 0

        failure_items = []
        for case in cases:
            if case['status'] not in (1, 2):
                continue
            if case['status'] == 1:
                status_class = 'failure'
                badge = '<span class="failure-status failure">失败</span>'
            else:
                status_class = 'error'
                badge = '<span class="failure-status error">错误</span>'
            failure_items.append(self.FAILURE_ITEM_TMPL % dict(
                status_class=status_class,
                badge=badge,
                name=saxutils.escape(case['name']),
                suite=saxutils.escape(case['suite']),
            ))

        if not failure_items:
            failure_html = '<div class="failure-empty"><i class="bi bi-check-circle me-2"></i> 暂无失败或错误用例</div>'
        else:
            failure_html = ''.join(failure_items)

        return self.INSIGHTS_TMPL % dict(
            screenshot_count=screenshot_count,
            screenshot_case_count=screenshot_case_count,
            output_case_count=output_case_count,
            avg_duration=self._format_duration(avg_duration),
            failure_items=failure_html,
        )

    def _generate_report(self, result):
        rows = []
        sortedResult = self.sortResult(result.result)
        for cid, (cls, cls_results) in enumerate(sortedResult):
            # subtotal for a class
            np = nf = ne = ns = 0
            class_duration = 0.0
            for n,t,o,e,*extra in cls_results:
                if n == 0: np += 1
                elif n == 1: nf += 1
                elif n == 2: ne += 1
                else: ns += 1
                class_duration += extra[1] if len(extra) > 1 else 0.0
            
            # format class description
            if cls.__module__ == "__main__":
                name = cls.__name__
            else:
                name = "%s.%s" % (cls.__module__, cls.__name__)
            doc = cls.__doc__ and cls.__doc__.split("\n")[0] or ""
            desc = doc and '%s: %s' % (name, doc) or name

            row = self.REPORT_CLASS_TMPL % dict(
                style = ne > 0 and 'errorClass' or nf > 0 and 'failClass' or ns > 0 and 'skipClass' or 'passClass',
                desc = desc,
                count = np+nf+ne+ns,
                Pass = np,
                fail = nf,
                error = ne,
                skip = ns,
                duration = self._format_duration(class_duration),
                cid = 'c%s' % (cid+1),
            )
            rows.append(row)

            for tid, (n,t,o,e,*extra) in enumerate(cls_results):
                screenshots = extra[0] if extra else []
                duration = extra[1] if len(extra) > 1 else 0.0
                self._generate_report_test(rows, cid, tid, n, t, o, e, screenshots, duration)

        report = self.REPORT_TMPL % dict(
            test_list = ''.join(rows),
            count = str(result.success_count+result.failure_count+result.error_count+result.skip_count),
            Pass = str(result.success_count),
            fail = str(result.failure_count),
            error = str(result.error_count),
            skip = str(result.skip_count),
        )
        return report

    def _generate_chart(self, result):
        suite_stats = []
        sortedResult = self.sortResult(result.result)

        for cls, cls_results in sortedResult:
            np = nf = ne = ns = 0
            for n, _t, _o, _e, *_extra in cls_results:
                if n == 0:
                    np += 1
                elif n == 1:
                    nf += 1
                elif n == 2:
                    ne += 1
                else:
                    ns += 1

            if cls.__module__ == "__main__":
                name = cls.__name__
            else:
                name = "%s.%s" % (cls.__module__, cls.__name__)

            suite_stats.append({
                'name': name,
                'pass': np,
                'fail': nf,
                'error': ne,
                'skip': ns,
            })

        chart = self.ECHARTS_SCRIPT % dict(
            Pass=str(result.success_count),
            fail=str(result.failure_count),
            error=str(result.error_count),
            skip=str(result.skip_count),
            suite_stats=json.dumps(suite_stats, ensure_ascii=False),
        )
        return chart

    def _format_duration(self, seconds):
        seconds = float(seconds or 0)
        if seconds < 1:
            milliseconds = seconds * 1000
            if milliseconds < 0.01:
                return '0 ms'
            return ('%.2f' % milliseconds).rstrip('0').rstrip('.') + ' ms'
        if seconds < 60:
            return ('%.2f' % seconds).rstrip('0').rstrip('.') + ' s'
        minutes = int(seconds // 60)
        remain_seconds = seconds % 60
        return '%dm %ss' % (minutes, ('%.2f' % remain_seconds).rstrip('0').rstrip('.'))

    def _generate_report_test(self, rows, cid, tid, n, t, o, e, screenshots=None, duration=0.0):
        # e.g. 'pt1.1', 'ft1.1', 'st1.1', etc
        # n == 0: pass, 1: fail, 2: error, 3: skip
        if n == 0:
            prefix = 'p'
        elif n == 3:
            prefix = 's'
        else:
            prefix = 'f'
        tid = prefix + 't%s.%s' % (cid+1,tid+1)
        name = t.id().split('.')[-1]
        doc = t.shortDescription() or ""
        desc = doc and ('%s: %s' % (name, doc)) or name
        
        # Always use the detail template so every case has an expandable detail panel.
        tmpl = self.REPORT_TEST_WITH_OUTPUT_TMPL

        script = self.REPORT_TEST_OUTPUT_TMPL % dict(
            id=tid,
            output=saxutils.escape(o+e) if (o or e) else '无输出信息',
        )

        # Generate screenshot HTML.
        screenshot_html = ''
        if screenshots and len(screenshots) > 0:
            count = len(screenshots)
            
            # Use carousel for multiple screenshots, grid for a single screenshot.
            if count >= 2:
                default_view = 'carousel'
                toggle_style = ''
                carousel_style = 'display: block;'
                grid_style = 'display: none;'
                btn_carousel_active = 'active'
                btn_grid_active = ''
            else:
                default_view = 'grid'
                toggle_style = ''
                carousel_style = 'display: none;'
                grid_style = 'display: grid;'
                btn_carousel_active = ''
                btn_grid_active = 'active'

            # Generate carousel items.
            carousel_items = []
            for i, screenshot in enumerate(screenshots):
                item = self.SCREENSHOT_CAROUSEL_ITEM_TMPL % {
                    'data': screenshot['data'],
                    'description': saxutils.escape(screenshot['description']),
                    'tid': tid,
                    'index': i
                }
                carousel_items.append(item)
            
            # Generate grid items.
            grid_items = []
            for i, screenshot in enumerate(screenshots):
                item = self.SCREENSHOT_GRID_ITEM_TMPL % {
                    'data': screenshot['data'],
                    'description': saxutils.escape(screenshot['description']),
                    'tid': tid,
                    'index': i
                }
                grid_items.append(item)
            
            # Generate carousel indicators.
            indicators = []
            for i in range(len(screenshots)):
                active_class = 'active' if i == 0 else ''
                indicators.append(f'<div class="screenshot-carousel-indicator {active_class}" onclick="goToSlide(\'{tid}\', {i})"></div>')
            
            screenshot_html = self.SCREENSHOT_TMPL % {
                'tid': tid,
                'count': count,
                'toggle_style': toggle_style,
                'carousel_style': carousel_style,
                'grid_style': grid_style,
                'btn_carousel_active': btn_carousel_active,
                'btn_grid_active': btn_grid_active,
                'carousel_items': ''.join(carousel_items),
                'grid_items': ''.join(grid_items),
                'indicators': ''.join(indicators)
            }

        if n == 0:
            style = 'passCase'
        elif n == 1:
            style = 'failCase'
        elif n == 2:
            style = 'errorCase'
        else:  # n == 3 (skip)
            style = 'skipCase'

        empty_cell = '<span class="case-empty-cell">&nbsp;</span>'
        status_cell = '<span class="case-status-pill %s">%s</span>' % (style, self.STATUS[n])

        row = tmpl % dict(
            tid=tid,
            Class=(n == 0 and 'hiddenRow' or 'none'),
            style=style,
            desc=desc,
            script=script,
            status=self.STATUS[n],
            status_class=style,
            pass_cell=status_cell if n == 0 else empty_cell,
            fail_cell=status_cell if n == 1 else empty_cell,
            error_cell=status_cell if n == 2 else empty_cell,
            skip_cell=status_cell if n == 3 else empty_cell,
            screenshots=screenshot_html,
            duration=self._format_duration(duration),
        )
        rows.append(row)

    def _generate_ending(self):
        return self.ENDING_TMPL


##############################################################################
# Facilities for running tests from the command line
##############################################################################

# Note: Reuse unittest.TestProgram to launch test. In the future we may
# build our own launcher to support more specific command line
# parameters like test title, CSS, etc.
class TestProgram(unittest.TestProgram):
    # A variation of unittest.TestProgram. Refer to the base class for
    # command line parameters.
    def runTests(self):
        # Pick UhtmlLit as the default test runner.
        # base class's testRunner parameter is not useful because it means
        # we have to instantiate UhtmlLit before we know self.verbosity.
        if self.testRunner is None:
            self.testRunner = UhtmlLit(verbosity=self.verbosity)
        unittest.TestProgram.runTests(self)

main = TestProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)

