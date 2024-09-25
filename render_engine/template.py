
def __o(inner):
    return f"<{inner.rstrip()}>"


def __c(tag):
    # NOTE: some tags don't have a closing tag
    empty_elements = ["area", "base", "br", "col", "embed", "hr",
                      "img", "input", "link", "meta", "source", "track", "wbr"]
    return "" if tag in empty_elements else f"</{tag}>"

# Only a small subset of html tags are needed right now
# for all others, use the ext_attr dictionary
def template(tag, c="", id="", ext_attr={}, body=('')):
    inner = f"{tag} "
    inner += f"class='{c}' " if c else ""
    inner += f"id='{id}' " if id else ""
    inner += ' '.join([f"{k}='{v}'" for k,
                      v in ext_attr.items()]) if ext_attr else ""

    # Normalize body if not already a tuple
    body = [str(body)] if not isinstance(body, tuple) else body

    return __o(inner) + "".join(body) + __c(tag)


if __name__ == "__main__":
    """
    <li class='font-weight-bold text-uppercase'>S</li>
    <li class='font-weight-bold text-uppercase'>M</li>
    <li class='font-weight-bold text-uppercase'>T</li>
    <li class='font-weight-bold text-uppercase'>W</li>
    <li class='font-weight-bold text-uppercase'>T</li>
    <li class='font-weight-bold text-uppercase'>F</li>
    <li class='font-weight-bold text-uppercase'>S</li>
    """
    days = ["M", "T", "W", "T", "F", "S", "S"]
    start_day = 6
    l = []
    for d in range(0, 7):
        l.append(template('li', c='font-weight-bold text-uppercase',
                 body=days[(d + start_day) % 7]))
    test1 = '\n'.join(l)
    print(test1)

    """
    <img src='smiley.gif'>
    """
    test2 = template('img', ext_attr={"src": "smiley.gif"})
    print(test2)

    """
    <br>
    """
    test3 = template('br')
    print(test3)

    """
    <div class='event'><span class='badge badge-dark'>8AM</span><i> 1st day of school</i></div>
    """
    test4 = template('div', c='event', body=(
        template('span', c='badge badge-dark', body='8AM'),
        template('i', body=' 1st day of school')
    )
    )
    print(test4)

    """
    <li>
        <div class="datecircle">1</div>
    </li>
    <li>
        <div class='date'>2</div>
        <div class='event'>Event 1 (all day)</div>
        <div class='event'>8AM: Event 2</div>
        <div class='event'>8PM: Event 3</div>
    </li>
    """
    # Pre-built events for a day
    test5_events = [
        "<div class='event'>Event 1 (all day)</div>",
        "<div class='event'>8AM: Event 2</div>",
        "<div class='event'>8PM: Event 3</div>"]

    test5 = template('li', body=(
        template('div', c='date', body=2),
        "".join(test5_events)
    )
    )
    print(test5)
