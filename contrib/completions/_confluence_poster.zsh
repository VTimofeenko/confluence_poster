#compdef confluence_poster

_confluence_poster_completion() {
  eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _CONFLUENCE_POSTER_COMPLETE=complete_zsh confluence_poster)
}

compdef _confluence_poster_completion confluence_poster
