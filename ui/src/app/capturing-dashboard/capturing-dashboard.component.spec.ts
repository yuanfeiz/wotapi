import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { CapturingDashboardComponent } from './capturing-dashboard.component';

describe('CapturingDashboardComponent', () => {
  let component: CapturingDashboardComponent;
  let fixture: ComponentFixture<CapturingDashboardComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ CapturingDashboardComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(CapturingDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
