import logging

from fastmcp.exceptions import PromptError
from fastmcp.exceptions import ResourceError
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware
from fastmcp.server.middleware import MiddlewareContext

logger = logging.getLogger(__name__)


class ReadOnlyTagMiddleware(Middleware):
    """
    Middleware that disables all tools, resources, or prompts that do NOT have the 'read-only' tag.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
            tags = getattr(tool, "tags", set())
            name = getattr(tool, "name", repr(tool))
            if "read-only" not in tags:
                logger.debug(f"[READ-ONLY] Disabling tool: {name} (tags: {tags})")
                if hasattr(tool, "disable"):
                    tool.disable()
                raise ToolError("This tool is disabled in read-only mode.")
        return await call_next(context)

    async def on_read_resource(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            resource = await context.fastmcp_context.fastmcp.get_resource(
                context.message.uri
            )
            tags = getattr(resource, "tags", set())
            name = getattr(resource, "name", repr(resource))
            if "read-only" not in tags:
                logger.debug(f"[READ-ONLY] Disabling resource: {name} (tags: {tags})")
                if hasattr(resource, "disable"):
                    resource.disable()
                raise ResourceError("This resource is disabled in read-only mode.")
        return await call_next(context)

    async def on_get_prompt(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            prompt = await context.fastmcp_context.fastmcp.get_prompt(
                context.message.name
            )
            tags = getattr(prompt, "tags", set())
            name = getattr(prompt, "name", repr(prompt))
            if "read-only" not in tags:
                logger.debug(f"[READ-ONLY] Disabling prompt: {name} (tags: {tags})")
                if hasattr(prompt, "disable"):
                    prompt.disable()
                raise PromptError("This prompt is disabled in read-only mode.")
        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.fastmcp_context:
            filtered = []
            for tool in result:
                tags = getattr(tool, "tags", set())
                if "read-only" in tags:
                    filtered.append(tool)
                elif hasattr(tool, "disable"):
                    tool.disable()
            return filtered
        return result

    async def on_list_resources(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.fastmcp_context:
            filtered = []
            for resource in result:
                tags = getattr(resource, "tags", set())
                if "read-only" in tags:
                    filtered.append(resource)
                elif hasattr(resource, "disable"):
                    resource.disable()
            return filtered
        return result

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.fastmcp_context:
            filtered = []
            for prompt in result:
                tags = getattr(prompt, "tags", set())
                if "read-only" in tags:
                    filtered.append(prompt)
                elif hasattr(prompt, "disable"):
                    prompt.disable()
            return filtered
        return result


class DisabledTagsMiddleware(Middleware):
    """
    Middleware that disables all tools, resources, or prompts that have any of the specified disabled tags.
    """

    def __init__(self, disabled_tags: set[str]):
        self.disabled_tags = disabled_tags

    def _has_disabled_tag(self, tags: set[str]) -> bool:
        return bool(self.disabled_tags.intersection(tags))

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
            tags = getattr(tool, "tags", set())
            if self._has_disabled_tag(tags):
                disabled_found = self.disabled_tags.intersection(tags)
                if hasattr(tool, "disable"):
                    tool.disable()
                raise ToolError(
                    f"This tool is disabled due to disabled tags: {disabled_found}"
                )
        return await call_next(context)

    async def on_read_resource(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            resource = await context.fastmcp_context.fastmcp.get_resource(
                context.message.uri
            )
            tags = getattr(resource, "tags", set())
            if self._has_disabled_tag(tags):
                disabled_found = self.disabled_tags.intersection(tags)
                if hasattr(resource, "disable"):
                    resource.disable()
                raise ResourceError(
                    f"This resource is disabled due to disabled tags: {disabled_found}"
                )
        return await call_next(context)

    async def on_get_prompt(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            prompt = await context.fastmcp_context.fastmcp.get_prompt(
                context.message.name
            )
            tags = getattr(prompt, "tags", set())
            if self._has_disabled_tag(tags):
                disabled_found = self.disabled_tags.intersection(tags)
                if hasattr(prompt, "disable"):
                    prompt.disable()
                raise PromptError(
                    f"This prompt is disabled due to disabled tags: {disabled_found}"
                )
        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.fastmcp_context:
            filtered = []
            for tool in result:
                tags = getattr(tool, "tags", set())
                if self._has_disabled_tag(tags):
                    if hasattr(tool, "disable"):
                        tool.disable()
                else:
                    filtered.append(tool)
            return filtered
        return result

    async def on_list_resources(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.fastmcp_context:
            filtered = []
            for resource in result:
                tags = getattr(resource, "tags", set())
                if self._has_disabled_tag(tags):
                    if hasattr(resource, "disable"):
                        resource.disable()
                else:
                    filtered.append(resource)
            return filtered
        return result

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.fastmcp_context:
            filtered = []
            for prompt in result:
                tags = getattr(prompt, "tags", set())
                if self._has_disabled_tag(tags):
                    if hasattr(prompt, "disable"):
                        prompt.disable()
                else:
                    filtered.append(prompt)
            return filtered
        return result
