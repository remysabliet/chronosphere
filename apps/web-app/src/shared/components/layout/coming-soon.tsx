import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';

export function ComingSoon({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className='text-muted-foreground'>This section is coming soon.</p>
      </CardContent>
    </Card>
  );
}
