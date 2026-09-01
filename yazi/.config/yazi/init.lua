function Entity:click(event, up)
	if up or event.is_middle then
		return
	end

	ya.emit("reveal", { self._file.url })

	if event.is_right then
		ya.emit("enter", {})
	end
end
