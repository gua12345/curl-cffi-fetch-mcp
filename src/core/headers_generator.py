"""浏览器指纹信息

动态获取 curl-cffi 支持的浏览器指纹列表
注意：curl-cffi 会根据 impersonate 参数自动设置合适的 headers，
我们不需要手动生成 headers，只需要提供支持的指纹列表供用户选择
"""

from typing import Dict, List
import re


def _extract_browser_types() -> List[str]:
    """
    从 curl_cffi.requests.BrowserType 动态提取所有支持的浏览器类型

    返回：
        浏览器类型列表
    """
    try:
        from curl_cffi.requests import BrowserType

        # 获取所有非私有属性
        all_attrs = dir(BrowserType)

        # 过滤出浏览器类型（排除字符串方法和私有属性）
        browser_types = [
            attr for attr in all_attrs
            if not attr.startswith('_') and not callable(getattr(str, attr, None))
        ]

        return browser_types
    except ImportError:
        # 如果 curl-cffi 未安装，返回空列表
        return []


def _generate_browser_description(browser_id: str) -> Dict[str, str]:
    """
    根据浏览器 ID 生成友好的名称和描述

    参数：
        browser_id: 浏览器类型标识符（如 chrome110, safari_ios）

    返回：
        包含 name 和 description 的字典
    """
    # 解析浏览器类型和版本
    browser_id_lower = browser_id.lower()

    # 通用浏览器（无版本号）
    if browser_id_lower == "chrome":
        return {"name": "Chrome (最新版本)", "description": "自动使用最新的 Chrome 浏览器指纹"}
    elif browser_id_lower == "chrome_android":
        return {"name": "Chrome Android (最新版本)", "description": "自动使用最新的 Chrome Android 浏览器指纹"}
    elif browser_id_lower == "firefox":
        return {"name": "Firefox (最新版本)", "description": "自动使用最新的 Firefox 浏览器指纹"}
    elif browser_id_lower == "safari":
        return {"name": "Safari (最新版本)", "description": "自动使用最新的 Safari 浏览器指纹"}
    elif browser_id_lower == "safari_ios":
        return {"name": "Safari iOS (最新版本)", "description": "自动使用最新的 Safari iOS 浏览器指纹"}

    # 带版本号的浏览器
    # Chrome 系列
    if browser_id_lower.startswith("chrome"):
        match = re.search(r'chrome(\d+)([a-z]*)(_android)?', browser_id_lower)
        if match:
            version = match.group(1)
            suffix = match.group(2) or ""
            is_android = match.group(3) is not None
            platform = " Android" if is_android else ""
            return {
                "name": f"Chrome {version}{suffix}{platform}",
                "description": f"Chrome {version}{suffix}{platform} 版本浏览器指纹"
            }

    # Edge 系列
    elif browser_id_lower.startswith("edge"):
        match = re.search(r'edge(\d+)', browser_id_lower)
        if match:
            version = match.group(1)
            return {
                "name": f"Edge {version}",
                "description": f"Microsoft Edge {version} 版本浏览器指纹"
            }

    # Firefox 系列
    elif browser_id_lower.startswith("firefox"):
        match = re.search(r'firefox(\d+)', browser_id_lower)
        if match:
            version = match.group(1)
            return {
                "name": f"Firefox {version}",
                "description": f"Firefox {version} 版本浏览器指纹"
            }

    # Safari 系列
    elif browser_id_lower.startswith("safari"):
        # 处理 safari15_3, safari153, safari17_2_ios 等格式
        match = re.search(r'safari(\d+)_?(\d*)(_ios)?', browser_id_lower)
        if match:
            major = match.group(1)
            minor = match.group(2)
            is_ios = match.group(3) is not None

            # 格式化版本号
            if len(major) == 3:  # safari153 -> 15.3
                version = f"{major[0:2]}.{major[2]}"
            elif len(major) == 2:  # safari18 -> 18.0
                version = f"{major}.{minor or '0'}"
            else:
                version = f"{major}.{minor}" if minor else major

            platform = " iOS" if is_ios else ""
            return {
                "name": f"Safari {version}{platform}",
                "description": f"Safari {version}{platform} 版本浏览器指纹"
            }

    # Tor 系列
    elif browser_id_lower.startswith("tor"):
        match = re.search(r'tor(\d+)', browser_id_lower)
        if match:
            version = match.group(1)
            # 格式化版本号 tor145 -> 14.5
            if len(version) == 3:
                version = f"{version[0:2]}.{version[2]}"
            return {
                "name": f"Tor {version}",
                "description": f"Tor Browser {version} 版本浏览器指纹"
            }

    # 默认返回
    return {
        "name": browser_id.replace("_", " ").title(),
        "description": f"{browser_id} 浏览器指纹"
    }


def get_supported_impersonates() -> List[Dict[str, str]]:
    """
    动态获取所有支持的 impersonate 参数列表

    返回：
        包含所有支持的浏览器指纹信息的列表
    """
    browser_types = _extract_browser_types()

    return [
        {
            "id": browser_id,
            **_generate_browser_description(browser_id)
        }
        for browser_id in browser_types
    ]


def is_valid_impersonate(impersonate: str) -> bool:
    """
    检查指定的 impersonate 参数是否有效

    参数：
        impersonate: 浏览器类型标识符

    返回：
        是否为有效的 impersonate 参数
    """
    browser_types = _extract_browser_types()
    return impersonate.lower() in [bt.lower() for bt in browser_types]

