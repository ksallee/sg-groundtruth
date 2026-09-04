// The corpus writes API literals in backticks, everywhere, including inside a
// one-line verdict. A verdict is rendered as text rather than through marked,
// so the backticks have to be turned into code spans by hand. Splitting beats
// rendering HTML here: three components need it, none needs anything else
// markdown does, and it takes no dependency.
//
// An odd number of backticks leaves the tail as plain text, which is what a
// reader wants from a typo: the character shows, nothing swallows the rest.
export function parts(text) {
	return String(text ?? '')
		.split('`')
		.map((s, i) => ({ text: s, code: i % 2 === 1 }));
}
