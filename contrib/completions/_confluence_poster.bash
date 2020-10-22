_confluence_poster_completion() {
    local IFS=$'
'
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _CONFLUENCE_POSTER_COMPLETE=complete_bash $1 ) )
    return 0
}
