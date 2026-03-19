"""HTML 到 Markdown 转换

使用 html2text 库将 HTML 内容转换为 Markdown 格式
"""

import html2text


def html_to_markdown(
    html_content: str,
    body_width: int = 0,
    ignore_links: bool = False,
    ignore_images: bool = False
) -> str:
    """
    将 HTML 转换为 Markdown

    参数：
        html_content: HTML 内容
        body_width: 文本宽度，0 表示不换行
        ignore_links: 是否忽略链接
        ignore_images: 是否忽略图片

    返回：
        Markdown 格式的文本
    """
    # 创建 html2text 转换器
    converter = html2text.HTML2Text()

    # 配置转换选项
    converter.body_width = body_width
    converter.ignore_links = ignore_links
    converter.ignore_images = ignore_images

    # 转换 HTML 为 Markdown
    markdown = converter.handle(html_content)

    return markdown
