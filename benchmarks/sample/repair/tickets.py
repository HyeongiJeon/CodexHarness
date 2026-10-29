def summarize(tickets):
    counts = {'open': 0, 'closed': 0, 'unknown': 0}
    for ticket in tickets:
        status = ticket.get('status')
        if status not in ('open', 'closed'):
            status = 'unknown'
        counts[status] += 1
    return counts
